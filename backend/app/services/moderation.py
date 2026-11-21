"""Reports, the moderation queue and the history shown to the affected user."""

import uuid
from typing import Literal

from sqlalchemy import String, and_, cast, distinct, func, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden, NotFound
from app.models.audit import AuditLog
from app.models.content import ContentItem, ContentStatus
from app.models.moderation import Report, ReportStatus
from app.models.user import User
from app.schemas.common import Page, parse_ts_cursor, ts_cursor
from app.schemas.content import AuthorOut
from app.schemas.moderation import (
    ItemRef,
    ModerationEvent,
    QueueItem,
    ReportIn,
    ReportOut,
)

# The audit actions a user may see about themselves (never who took them).
HISTORY_ACTIONS = (
    "content.hide",
    "content.unhide",
    "content.approve",
    "user.mute",
    "user.unmute",
    "user.ban",
    "user.unban",
)


async def create_report(
    db: AsyncSession, user: User, item_id: uuid.UUID, body: ReportIn
) -> None:
    item = await db.get(ContentItem, item_id)
    if item is None or item.status != ContentStatus.published:
        raise NotFound("Not found.")
    if item.author_id == user.id:
        raise Forbidden("You cannot report your own post.", code="self_report")
    inserted = await db.scalar(
        pg_insert(Report)
        .values(
            item_id=item.id,
            reporter_id=user.id,
            reason=body.reason.value,
            note=body.note.strip(),
        )
        .on_conflict_do_nothing(index_elements=["item_id", "reporter_id"])
        .returning(Report.id)
    )
    if inserted is None:
        raise Conflict("You already reported this.", code="already_reported")


async def item_reports(db: AsyncSession, item_id: uuid.UUID) -> list[ReportOut]:
    """Newest 100 reports on one item (open first), for the admin detail drawer."""
    rows = await db.scalars(
        select(Report)
        .where(Report.item_id == item_id)
        .order_by((Report.status != ReportStatus.open.value), Report.created_at.desc())
        .limit(100)
    )
    return [ReportOut.model_validate(r, from_attributes=True) for r in rows]


async def queue(
    db: AsyncSession,
    view: Literal["reports", "pending", "hidden"],
    type_: str | None,
    reason: str | None,
    cursor: str | None,
    limit: int,
) -> Page[QueueItem]:
    """Items that need a moderator: with open reports, awaiting review, or hidden.

    With a `reason` filter the report count and reasons cover only matching reports.
    """
    open_reports = select(
        Report.item_id,
        func.count().label("n"),
        func.max(Report.created_at).label("last"),
        func.array_agg(distinct(Report.reason)).label("reasons"),
    ).where(Report.status == ReportStatus.open.value)
    if reason:
        open_reports = open_reports.where(Report.reason == reason)
    agg = open_reports.group_by(Report.item_id).subquery()
    ts = {
        "reports": agg.c.last,
        "pending": ContentItem.created_at,
        "hidden": ContentItem.updated_at,
    }[view]
    stmt = select(
        ContentItem,
        func.coalesce(agg.c.n, 0),
        func.coalesce(agg.c.reasons, []),
        ts.label("ts"),
    )
    if view == "reports":
        stmt = stmt.join(agg, agg.c.item_id == ContentItem.id)
    else:
        stmt = stmt.outerjoin(agg, agg.c.item_id == ContentItem.id).where(
            ContentItem.status
            == (
                ContentStatus.pending_review
                if view == "pending"
                else ContentStatus.hidden
            ).value
        )
    if type_:
        stmt = stmt.where(ContentItem.type == type_)
    if cursor:
        stmt = stmt.where(tuple_(ts, ContentItem.id) < tuple_(*parse_ts_cursor(cursor)))
    rows = (
        await db.execute(
            stmt.order_by(ts.desc(), ContentItem.id.desc()).limit(limit + 1)
        )
    ).all()
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = ts_cursor(rows[-1].ts, rows[-1][0].id)
    return Page(
        items=[
            QueueItem(
                id=i.id,
                type=i.type,
                call_number=i.call_number,
                title=i.title,
                status=i.status,
                hidden_reason=i.hidden_reason,
                author=AuthorOut.model_validate(i.author),
                report_count=n,
                reasons=sorted(reasons),
                created_at=i.created_at,
                activity_at=at,
            )
            for i, n, reasons, at in rows
        ],
        next_cursor=nxt,
    )


async def history(
    db: AsyncSession, user: User, cursor: str | None, limit: int
) -> Page[ModerationEvent]:
    """Moderation actions taken on the user's account or on their content, newest first."""
    stmt = (
        select(AuditLog, ContentItem)
        .outerjoin(
            ContentItem,
            and_(
                AuditLog.target_type == "content_item",
                AuditLog.target_id == cast(ContentItem.id, String),
            ),
        )
        .where(
            AuditLog.action.in_(HISTORY_ACTIONS),
            or_(
                and_(
                    AuditLog.target_type == "user", AuditLog.target_id == str(user.id)
                ),
                ContentItem.author_id == user.id,
            ),
        )
    )
    if cursor:
        stmt = stmt.where(
            tuple_(AuditLog.created_at, AuditLog.id) < tuple_(*parse_ts_cursor(cursor))
        )
    rows = (
        await db.execute(
            stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(
                limit + 1
            )
        )
    ).all()
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = ts_cursor(rows[-1][0].created_at, rows[-1][0].id)
    return Page(
        items=[
            ModerationEvent(
                id=log.id,
                action=log.action,
                reason=log.reason,
                created_at=log.created_at,
                item=item_ref(item) if item else None,
            )
            for log, item in rows
        ],
        next_cursor=nxt,
    )


def item_ref(item: ContentItem) -> ItemRef:
    return ItemRef(
        id=item.id,
        call_number=item.call_number,
        title=item.title,
        status=item.status,
    )
