"""Admin actions on content: hide, unhide, approve, dismiss reports. Every one is audited."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict, NotFound
from app.models.content import ContentItem, ContentStatus
from app.models.moderation import Report, ReportStatus
from app.models.qa import NotificationKind
from app.models.user import User
from app.schemas.moderation import ActionFailure, ActionResult, ContentAction
from app.services import audit, notifications

# action -> (statuses it may start from, status it leads to)
_MOVES = {
    "hide": (
        {ContentStatus.published, ContentStatus.pending_review},
        ContentStatus.hidden,
    ),
    "unhide": ({ContentStatus.hidden}, ContentStatus.published),
    "approve": ({ContentStatus.pending_review}, ContentStatus.published),
}


async def _close_reports(
    db: AsyncSession, actor: User, item_id: uuid.UUID, status: ReportStatus
) -> int:
    res = await db.execute(
        update(Report)
        .where(Report.item_id == item_id, Report.status == ReportStatus.open.value)
        .values(
            status=status.value, resolved_by_id=actor.id, resolved_at=datetime.now(UTC)
        )
    )
    return res.rowcount  # type: ignore[attr-defined]


async def apply(
    db: AsyncSession,
    actor: User,
    action: str,
    item_id: uuid.UUID,
    reason: str | None,
) -> None:
    item = await db.get(ContentItem, item_id, with_for_update={"of": ContentItem})
    if item is None:
        raise NotFound("Not found.")
    if action == "dismiss":
        n = await _close_reports(db, actor, item.id, ReportStatus.dismissed)
        if not n:
            raise Conflict("There are no open reports on this item.")
        await audit.record(
            db,
            actor_id=actor.id,
            action="report.dismiss",
            target_type="content_item",
            target_id=item.id,
            before={"open_reports": n},
            after={"open_reports": 0},
            reason=reason,
        )
        return
    allowed, target = _MOVES[action]
    if ContentStatus(item.status) not in allowed:
        raise Conflict(f"Cannot {action} an item that is {item.status}.")
    before = {"status": item.status, "hidden_reason": item.hidden_reason}
    item.status = target.value
    item.hidden_reason = reason if action == "hide" else None
    await audit.record(
        db,
        actor_id=actor.id,
        action=f"content.{action}",
        target_type="content_item",
        target_id=item.id,
        before=before,
        after={"status": item.status, "hidden_reason": item.hidden_reason},
        reason=reason,
    )
    if action == "hide":
        await _close_reports(db, actor, item.id, ReportStatus.actioned)
    await notifications.notify(
        db,
        item.author_id,
        NotificationKind.moderation,
        item.id,
        actor=actor,
        message=reason or "approved and visible again",
    )
    await db.flush()


async def apply_many(
    db: AsyncSession, actor: User, body: ContentAction
) -> ActionResult:
    """Each id succeeds or fails on its own (savepoint), so one bad row never blocks the rest."""
    done, failed = [], []
    for item_id in body.ids:
        try:
            async with db.begin_nested():
                await apply(db, actor, body.action, item_id, body.reason)
            done.append(item_id)
        except AppError as exc:
            failed.append(ActionFailure(id=item_id, message=exc.message))
    return ActionResult(done=done, failed=failed)


async def restore(db: AsyncSession, actor: User, item_id: uuid.UUID) -> None:
    """Legacy `publish`: approve a pending item, unhide a hidden one, ignore a published one."""
    status = await db.scalar(
        select(ContentItem.status).where(ContentItem.id == item_id)
    )
    if status is None:
        raise NotFound("Not found.")
    if status == ContentStatus.hidden:
        await apply(db, actor, "unhide", item_id, None)
    elif status == ContentStatus.pending_review:
        await apply(db, actor, "approve", item_id, None)
