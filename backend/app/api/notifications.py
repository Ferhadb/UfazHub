from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, CurrentUser
from app.core.ratelimit import limit_write
from app.schemas.common import Page
from app.schemas.notifications import (
    NotificationOut,
    NotificationSettings,
    ReadIn,
    UnreadOut,
)
from app.schemas.reputation import ReputationEventOut, ReputationRules
from app.services import notifications as svc
from app.services import reputation

router = APIRouter(tags=["notifications"])


@router.get("/notifications", response_model=Page[NotificationOut])
async def list_notifications(
    db: DB,
    user: CurrentUser,
    unread: bool = False,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await svc.list_for(db, user, unread, cursor, limit)


@router.get("/notifications/unread", response_model=UnreadOut)
async def unread(db: DB, user: CurrentUser):
    return UnreadOut(unread=await svc.unread_count(db, user))


@router.post(
    "/notifications/read",
    response_model=UnreadOut,
    dependencies=[Depends(limit_write)],
)
async def mark_read(body: ReadIn, db: DB, user: CurrentUser):
    n = await svc.mark_read(db, user, body.ids)
    await db.commit()
    return UnreadOut(unread=n)


@router.get("/notifications/settings", response_model=NotificationSettings)
async def get_settings(user: CurrentUser):
    return NotificationSettings(email_digest=user.email_digest)


@router.put(
    "/notifications/settings",
    response_model=NotificationSettings,
    dependencies=[Depends(limit_write)],
)
async def put_settings(body: NotificationSettings, db: DB, user: CurrentUser):
    user.email_digest = body.email_digest
    await db.commit()
    return body


@router.get("/reputation/rules", response_model=ReputationRules)
async def reputation_rules():
    """Public: the points table and privilege thresholds, straight from the code that enforces them."""
    return reputation.rules()


@router.get("/me/reputation", response_model=Page[ReputationEventOut])
async def my_reputation(
    db: DB,
    user: CurrentUser,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await reputation.history(db, user, cursor, limit)
