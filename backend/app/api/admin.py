"""Admin panel API: moderation queue, content and user actions, appeals, audit log."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import AdminUser, admin_user
from app.core.ratelimit import limit_write
from app.models.content import ContentType
from app.models.moderation import AppealStatus, ReportReason
from app.models.user import Role, UserStatus
from app.schemas.common import Page
from app.schemas.moderation import (
    ActionResult,
    AppealOut,
    AppealResolveIn,
    AuditOut,
    ContentAction,
    QueueItem,
    ReportOut,
    UserAdminOut,
    UserRoleIn,
    UserStatusIn,
)
from app.services import appeals, audit, content_admin, moderation, users_admin

# `AdminUser` on the router: every route below needs an unmuted, unbanned admin.
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(admin_user)])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=100)]


@router.get("/queue", response_model=Page[QueueItem])
async def queue(
    db: DB,
    view: Literal["reports", "pending", "hidden"] = "reports",
    type: ContentType | None = None,
    reason: ReportReason | None = None,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    return await moderation.queue(
        db,
        view,
        type.value if type else None,
        reason.value if reason else None,
        cursor,
        limit,
    )


@router.get("/content/{item_id}/reports", response_model=list[ReportOut])
async def item_reports(item_id: uuid.UUID, db: DB):
    return await moderation.item_reports(db, item_id)


@router.post(
    "/content/actions",
    response_model=ActionResult,
    dependencies=[Depends(limit_write)],
)
async def content_actions(body: ContentAction, db: DB, admin: AdminUser):
    out = await content_admin.apply_many(db, admin, body)
    await db.commit()
    return out


@router.get("/users", response_model=Page[UserAdminOut])
async def users(
    db: DB,
    q: Annotated[str | None, Query(max_length=80)] = None,
    role: Role | None = None,
    status: UserStatus | None = None,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    return await users_admin.list_users(
        db,
        q,
        role.value if role else None,
        status.value if status else None,
        cursor,
        limit,
    )


@router.put(
    "/users/{user_id}/status",
    response_model=UserAdminOut,
    dependencies=[Depends(limit_write)],
)
async def user_status(user_id: uuid.UUID, body: UserStatusIn, db: DB, admin: AdminUser):
    user = await users_admin.set_status(db, admin, user_id, body.status, body.reason)
    await db.commit()
    return user


@router.put(
    "/users/{user_id}/role",
    response_model=UserAdminOut,
    dependencies=[Depends(limit_write)],
)
async def user_role(user_id: uuid.UUID, body: UserRoleIn, db: DB, admin: AdminUser):
    user = await users_admin.set_role(db, admin, user_id, body.role, body.reason)
    await db.commit()
    return user


@router.get("/appeals", response_model=Page[AppealOut])
async def list_appeals(
    db: DB,
    status: AppealStatus | None = AppealStatus.open,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    return await appeals.list_appeals(
        db,
        user_id=None,
        status=status.value if status else None,
        cursor=cursor,
        limit=limit,
    )


@router.post(
    "/appeals/{appeal_id}/resolve",
    status_code=204,
    dependencies=[Depends(limit_write)],
)
async def resolve_appeal(
    appeal_id: uuid.UUID, body: AppealResolveIn, db: DB, admin: AdminUser
):
    await appeals.resolve(
        db, admin, appeal_id, body.decision == "accept", body.response
    )
    await db.commit()


@router.get("/audit", response_model=Page[AuditOut])
async def audit_log(
    db: DB,
    actor_id: uuid.UUID | None = None,
    action: Annotated[str | None, Query(max_length=64)] = None,
    target_type: Annotated[str | None, Query(max_length=32)] = None,
    target_id: Annotated[str | None, Query(max_length=64)] = None,
    cursor: Cursor = None,
    limit: Limit = 30,
):
    return await audit.list_log(
        db,
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        cursor=cursor,
        limit=limit,
    )
