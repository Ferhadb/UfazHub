import uuid
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import request_id_var
from app.models.audit import AuditLog


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
