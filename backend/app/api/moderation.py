"""What any signed-in user can do about moderation: report, appeal, see their own history."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, CurrentUser
from app.api.permissions import VerifiedUser
from app.core.ratelimit import limit_auth, limit_write
from app.schemas.common import Page
from app.schemas.moderation import (
    AppealIn,
    AppealOut,
    BanAppealIn,
    ModerationEvent,
    ReportIn,
)
from app.services import appeals, moderation

router = APIRouter(tags=["moderation"])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=50)]


@router.post(
    "/content/{item_id}/report",
    status_code=204,
    dependencies=[Depends(limit_write)],
)
async def report(item_id: uuid.UUID, body: ReportIn, db: DB, user: VerifiedUser):
    await moderation.create_report(db, user, item_id, body)
    await db.commit()


# Appealing is not a content write: a muted author may still ask for their post back.
@router.post(
    "/content/{item_id}/appeal", status_code=204, dependencies=[Depends(limit_write)]
)
async def appeal_content(item_id: uuid.UUID, body: AppealIn, db: DB, user: CurrentUser):
    await appeals.appeal_content(db, user, item_id, body.message)
    await db.commit()


@router.post("/auth/appeal", status_code=204, dependencies=[Depends(limit_auth)])
async def appeal_ban(body: BanAppealIn, db: DB):
    await appeals.appeal_ban(db, body.email, body.password, body.message)
    await db.commit()


@router.get("/me/moderation", response_model=Page[ModerationEvent])
async def my_history(
    db: DB, user: CurrentUser, cursor: Cursor = None, limit: Limit = 20
):
    return await moderation.history(db, user, cursor, limit)


@router.get("/me/appeals", response_model=Page[AppealOut])
async def my_appeals(
    db: DB, user: CurrentUser, cursor: Cursor = None, limit: Limit = 20
):
    return await appeals.list_appeals(
        db, user_id=user.id, status=None, cursor=cursor, limit=limit
    )
