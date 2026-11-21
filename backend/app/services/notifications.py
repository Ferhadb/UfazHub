"""In-app notifications (fan-out helpers other services call) plus the daily email digest."""

import uuid
from datetime import datetime

from sqlalchemy import func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.config import settings
from app.core.errors import AppError
from app.core.mail import send_mail
from app.models.content import ContentItem
from app.models.qa import Answer, Notification, NotificationKind
from app.models.user import User
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.notifications import NotificationOut

MILESTONES = (10, 25, 50, 100, 250, 500)
DIGEST_BATCH = 2000  # notifications per digest run; the rest goes out next time


async def page_ref(db: AsyncSession, item_id: uuid.UUID) -> tuple[str, str]:
    """(call number, title) of the page that shows this item; an answer lives on its question."""
    q = aliased(ContentItem)
    row = (
        await db.execute(
            select(
                func.coalesce(q.call_number, ContentItem.call_number), ContentItem.title
            )
            .select_from(ContentItem)
            .outerjoin(Answer.__table__, Answer.__table__.c.id == ContentItem.id)
            .outerjoin(q, q.id == Answer.__table__.c.question_id)
            .where(ContentItem.id == item_id)
        )
    ).one()
    return row[0], row[1]


async def notify(
    db: AsyncSession,
    user_id: uuid.UUID,
    kind: NotificationKind,
    item_id: uuid.UUID,
    *,
    actor: User | None = None,
    message: str = "",
    dedupe_key: str | None = None,
) -> None:
    """Never notifies you about your own actions; a repeated `dedupe_key` is ignored."""
    if actor is not None and actor.id == user_id:
        return
    call_number, title = await page_ref(db, item_id)
    await db.execute(
        pg_insert(Notification)
        .values(
            user_id=user_id,
            kind=kind.value,
            actor_id=actor.id if actor else None,
            item_id=item_id,
            call_number=call_number,
            title=title[:200],
            message=message[:500],
            dedupe_key=dedupe_key,
        )
        .on_conflict_do_nothing(index_elements=["user_id", "dedupe_key"])
    )


async def vote_milestone(
    db: AsyncSession, author_id: uuid.UUID, item_id: uuid.UUID, old: int, new: int
) -> None:
    for m in MILESTONES:
        if old < m <= new:
            await notify(
                db,
                author_id,
                NotificationKind.vote_milestone,
                item_id,
                message=f"{m} votes",
                dedupe_key=f"milestone:{item_id}:{m}",
            )


async def list_for(
    db: AsyncSession, user: User, unread_only: bool, cursor: str | None, limit: int
) -> Page[NotificationOut]:
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    if cursor:
        try:
            raw = decode_cursor(cursor)["k"]
            key = (datetime.fromisoformat(raw[0]), uuid.UUID(raw[1]))
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
        stmt = stmt.where(
            tuple_(Notification.created_at, Notification.id) < tuple_(*key)
        )
    rows = list(
        (
            await db.execute(
                stmt.order_by(
                    Notification.created_at.desc(), Notification.id.desc()
                ).limit(limit + 1)
            )
        )
        .scalars()
        .all()
    )
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = encode_cursor({"k": [rows[-1].created_at.isoformat(), str(rows[-1].id)]})
    actors = {}
    ids = {r.actor_id for r in rows if r.actor_id}
    if ids:
        actors = {
            u.id: u
            for u in (await db.execute(select(User).where(User.id.in_(ids)))).scalars()
        }
    return Page(
        items=[
            NotificationOut(
                id=r.id,
                kind=r.kind,
                actor=actors.get(r.actor_id),  # type: ignore[arg-type]
                call_number=r.call_number,
                title=r.title,
                message=r.message,
                read=r.read_at is not None,
                created_at=r.created_at,
            )
            for r in rows
        ],
        next_cursor=nxt,
    )


async def unread_count(db: AsyncSession, user: User) -> int:
    return (
        await db.scalar(
            select(func.count()).where(
                Notification.user_id == user.id, Notification.read_at.is_(None)
            )
        )
        or 0
    )


async def mark_read(db: AsyncSession, user: User, ids: list[uuid.UUID] | None) -> int:
    stmt = update(Notification).where(
        Notification.user_id == user.id, Notification.read_at.is_(None)
    )
    if ids is not None:
        stmt = stmt.where(Notification.id.in_(ids))
    await db.execute(stmt.values(read_at=func.now()))
    return await unread_count(db, user)


def describe(n: Notification) -> str:
    kind = NotificationKind(n.kind)
    what = {
        NotificationKind.reply: "New reply on",
        NotificationKind.answer: "New answer on",
        NotificationKind.answer_accepted: "Your answer was accepted on",
        NotificationKind.vote_milestone: f"{n.message} on",
        NotificationKind.moderation: (
            f"Moderation ({n.message}):" if n.message else "Moderation:"
        ),
    }[kind]
    return f"{what} {n.call_number} {n.title}"


async def send_digests(db: AsyncSession) -> int:
    """One email per opted-in user listing notifications still unread and never emailed. Returns mails sent."""
    rows = (
        await db.execute(
            select(Notification, User.email)
            .join(User, User.id == Notification.user_id)
            .where(
                User.email_digest.is_(True),
                Notification.read_at.is_(None),
                Notification.emailed_at.is_(None),
            )
            .order_by(Notification.user_id, Notification.created_at)
            .limit(DIGEST_BATCH)
        )
    ).all()
    by_user: dict[str, list[Notification]] = {}
    for n, email in rows:
        by_user.setdefault(email, []).append(n)
    for email, items in by_user.items():
        lines = [f"- {describe(n)} ({settings.SITE_URL}/notifications)" for n in items]
        await send_mail(
            email,
            f"{len(items)} unread on UFAZ Hub",
            "While you were away:\n\n" + "\n".join(lines),
        )
        await db.execute(
            update(Notification)
            .where(Notification.id.in_([n.id for n in items]))
            .values(emailed_at=func.now())
        )
    await db.commit()
    return len(by_user)
