"""Appeals: an author contests a hidden item, a banned user contests the ban."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, NotFound, Unauthorized
from app.core.security import verify_password
from app.models.content import ContentItem, ContentStatus
from app.models.moderation import Appeal, AppealKind, AppealStatus
from app.models.qa import NotificationKind
from app.models.user import User, UserStatus
from app.schemas.common import Page, parse_ts_cursor, ts_cursor
from app.schemas.content import AuthorOut
from app.schemas.moderation import AppealOut
from app.services import audit, auth, content_admin, notifications, users_admin
from app.services.moderation import item_ref


async def _open(db: AsyncSession, **values) -> None:
    created = await db.scalar(
        pg_insert(Appeal)
        .values(status=AppealStatus.open.value, **values)
        .on_conflict_do_nothing()  # the partial unique indexes: one open appeal per subject
        .returning(Appeal.id)
    )
    if created is None:
        raise Conflict("You already have an open appeal for this.", code="appeal_open")


async def appeal_content(
    db: AsyncSession, user: User, item_id: uuid.UUID, message: str
) -> None:
    item = await db.get(ContentItem, item_id)
    if item is None or item.author_id != user.id:
        raise NotFound("Not found.")
    if item.status != ContentStatus.hidden:
        raise Conflict("Only hidden posts can be appealed.", code="not_hidden")
    await _open(
        db,
        user_id=user.id,
        kind=AppealKind.content.value,
        item_id=item.id,
        message=message,
    )


async def appeal_ban(db: AsyncSession, email: str, password: str, message: str) -> None:
    """A banned user cannot hold a session, so the password proves who is asking."""
    user = await auth.get_user_by_email(db, email)
    if (
        not await verify_password(user.password_hash if user else None, password)
        or not user
    ):
        raise Unauthorized("Wrong email or password.", code="invalid_credentials")
    if user.status != UserStatus.banned:
        raise Conflict("This account is not suspended.", code="not_banned")
    await _open(db, user_id=user.id, kind=AppealKind.ban.value, message=message)


async def list_appeals(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None,
    status: str | None,
    cursor: str | None,
    limit: int,
) -> Page[AppealOut]:
    stmt = select(Appeal, ContentItem).outerjoin(
        ContentItem, ContentItem.id == Appeal.item_id
    )
    if user_id:
        stmt = stmt.where(Appeal.user_id == user_id)
    if status:
        stmt = stmt.where(Appeal.status == status)
    if cursor:
        stmt = stmt.where(
            tuple_(Appeal.created_at, Appeal.id) < tuple_(*parse_ts_cursor(cursor))
        )
    rows = (
        await db.execute(
            stmt.order_by(Appeal.created_at.desc(), Appeal.id.desc()).limit(limit + 1)
        )
    ).all()
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = ts_cursor(rows[-1][0].created_at, rows[-1][0].id)
    return Page(items=[_out(a, i) for a, i in rows], next_cursor=nxt)


def _out(a: Appeal, item: ContentItem | None) -> AppealOut:
    return AppealOut(
        id=a.id,
        kind=a.kind,
        status=a.status,
        message=a.message,
        response=a.response,
        user=AuthorOut.model_validate(a.user),
        item=item_ref(item) if item else None,
        created_at=a.created_at,
        resolved_at=a.resolved_at,
    )


async def resolve(
    db: AsyncSession, actor: User, appeal_id: uuid.UUID, accept: bool, response: str
) -> None:
    appeal = await db.get(Appeal, appeal_id, with_for_update={"of": Appeal})
    if appeal is None:
        raise NotFound("No such appeal.")
    if appeal.status != AppealStatus.open:
        raise Conflict("This appeal is already resolved.", code="appeal_closed")
    item = await db.get(ContentItem, appeal.item_id) if appeal.item_id else None
    if accept:
        if item is not None and item.status == ContentStatus.hidden:
            await content_admin.apply(db, actor, "unhide", item.id, response)
        elif item is None:
            await users_admin.set_status(
                db, actor, appeal.user_id, UserStatus.active, response
            )
    elif item is not None:
        await notifications.notify(
            db,
            item.author_id,
            NotificationKind.moderation,
            item.id,
            actor=actor,
            message=f"Appeal rejected: {response}",
        )
    appeal.status = (AppealStatus.accepted if accept else AppealStatus.rejected).value
    appeal.response = response
    appeal.resolved_by_id = actor.id
    appeal.resolved_at = datetime.now(UTC)
    await audit.record(
        db,
        actor_id=actor.id,
        action="appeal.accept" if accept else "appeal.reject",
        target_type="appeal",
        target_id=appeal.id,
        before={"status": AppealStatus.open.value},
        after={"status": appeal.status},
        reason=response,
    )
    await db.flush()
