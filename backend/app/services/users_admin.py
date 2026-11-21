"""Admin actions on accounts: mute, ban, unban and role changes. Every one is audited."""

import uuid

from sqlalchemy import or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden, NotFound
from app.models.user import Role, User, UserStatus
from app.schemas.common import Page, parse_ts_cursor, ts_cursor
from app.schemas.moderation import UserAdminOut
from app.services import audit
from app.services.auth import revoke_all


def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


async def list_users(
    db: AsyncSession,
    q: str | None,
    role: str | None,
    status: str | None,
    cursor: str | None,
    limit: int,
) -> Page[UserAdminOut]:
    stmt = select(User)
    if q:
        stmt = stmt.where(
            or_(
                User.email.ilike(_like(q), escape="\\"),
                User.display_name.ilike(_like(q), escape="\\"),
            )
        )
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)
    if cursor:
        stmt = stmt.where(
            tuple_(User.created_at, User.id) < tuple_(*parse_ts_cursor(cursor))
        )
    rows = list(
        (
            await db.scalars(
                stmt.order_by(User.created_at.desc(), User.id.desc()).limit(limit + 1)
            )
        )
    )
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = ts_cursor(rows[-1].created_at, rows[-1].id)
    return Page(
        items=[UserAdminOut.model_validate(u, from_attributes=True) for u in rows],
        next_cursor=nxt,
    )


async def _target(db: AsyncSession, actor: User, user_id: uuid.UUID) -> User:
    user = await db.get(User, user_id, with_for_update=True)
    if user is None:
        raise NotFound("No such user.")
    if user.id == actor.id:
        raise Forbidden("You cannot change your own account.", code="self_action")
    return user


async def set_status(
    db: AsyncSession,
    actor: User,
    user_id: uuid.UUID,
    status: UserStatus,
    reason: str,
) -> User:
    user = await _target(db, actor, user_id)
    if user.role == Role.admin:
        raise Conflict("Remove the admin role before muting or banning.")
    if user.status == status:
        raise Conflict(f"This user is already {status.value}.")
    before = user.status
    user.status = status.value
    verb = {
        UserStatus.muted: "mute",
        UserStatus.banned: "ban",
        UserStatus.active: "unban" if before == UserStatus.banned else "unmute",
    }[status]
    await audit.record(
        db,
        actor_id=actor.id,
        action=f"user.{verb}",
        target_type="user",
        target_id=user.id,
        before={"status": before},
        after={"status": user.status},
        reason=reason,
    )
    if status == UserStatus.banned:
        await revoke_all(db, user.id)  # sessions end now; login and refresh refuse them
    await db.flush()
    return user


async def set_role(
    db: AsyncSession, actor: User, user_id: uuid.UUID, role: Role, reason: str
) -> User:
    user = await _target(db, actor, user_id)
    if user.role == role:
        raise Conflict(f"This user is already {role.value}.")
    before = user.role
    user.role = role.value
    await audit.record(
        db,
        actor_id=actor.id,
        action="user.role",
        target_type="user",
        target_id=user.id,
        before={"role": before},
        after={"role": user.role},
        reason=reason,
    )
    await db.flush()
    return user
