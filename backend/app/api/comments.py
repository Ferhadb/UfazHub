import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import ActiveUser, VerifiedUser
from app.core.ratelimit import limit_comment
from app.schemas.comments import CommentIn, CommentOut
from app.schemas.common import Page
from app.services import comments as svc

router = APIRouter(tags=["comments"])


@router.get("/content/{item_id}/comments", response_model=Page[CommentOut])
async def list_comments(
    item_id: uuid.UUID,
    db: DB,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await svc.list_comments(db, item_id, cursor, limit)


@router.post(
    "/content/{item_id}/comments",
    status_code=201,
    response_model=CommentOut,
    dependencies=[Depends(limit_comment)],
)
async def create_comment(
    item_id: uuid.UUID, body: CommentIn, db: DB, user: VerifiedUser
):
    out = await svc.create_comment(db, user, item_id, body)
    await db.commit()
    return out


@router.delete(
    "/comments/{comment_id}", status_code=204, dependencies=[Depends(limit_comment)]
)
async def delete_comment(comment_id: uuid.UUID, db: DB, user: ActiveUser):
    await svc.delete_comment(db, user, comment_id)
    await db.commit()
