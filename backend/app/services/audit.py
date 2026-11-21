import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_var
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.common import Page, parse_ts_cursor, ts_cursor
from app.schemas.content import AuthorOut
from app.schemas.moderation import AuditOut


def diff(before: dict[str, Any] | None, after: dict[str, Any] | None):
    """Keep only the keys whose value changed, so rows stay small."""
    b, a = before or {}, after or {}
    keys = {k for k in b.keys() | a.keys() if b.get(k) != a.get(k)}
    # jsonable_encoder: values may be UUIDs or datetimes, which JSONB cannot store as-is.
    return (
        jsonable_encoder({k: b.get(k) for k in keys}) or None,
        jsonable_encoder({k: a.get(k) for k in keys}) or None,
    )


async def record(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target_type: str,
    target_id: str | uuid.UUID,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AuditLog:
    """Add an audit row to the caller's transaction (it commits with the change itself)."""
    b, a = diff(before, after)
    row = AuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        before=b,
        after=a,
        reason=reason,
        request_id=request_id_var.get(),
    )
    db.add(row)
    return row


async def list_log(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str | None,
    target_type: str | None,
    target_id: str | None,
    cursor: str | None,
    limit: int,
) -> Page[AuditOut]:
    stmt = select(AuditLog, User).outerjoin(User, User.id == AuditLog.actor_id)
    for col, val in (
        (AuditLog.actor_id, actor_id),
        (AuditLog.action, action),
        (AuditLog.target_type, target_type),
        (AuditLog.target_id, target_id),
    ):
        if val is not None:
            stmt = stmt.where(col == val)
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
            AuditOut(
                actor=AuthorOut.model_validate(actor) if actor else None,
                **{f: getattr(log, f) for f in AuditOut.model_fields if f != "actor"},
            )
            for log, actor in rows
        ],
        next_cursor=nxt,
    )
