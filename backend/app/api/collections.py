import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import (
    ActiveUser,
    OptionalUser,
    VerifiedUser,
    can_manage,
    not_found_unless_visible,
)
from app.core.errors import Forbidden, NotFound
from app.core.ratelimit import limit_write
from app.models.content import Collection, ContentStatus
from app.schemas.collections import CollectionIn, CollectionOut, CollectionPatch
from app.schemas.common import Page
from app.services import collections as svc

router = APIRouter(tags=["collections"])


@router.get("/collections", response_model=Page[CollectionOut])
async def list_collections(
    db: DB,
    viewer: OptionalUser,
    sort: Literal["latest", "top"] = "latest",
    tag: Annotated[str | None, Query(max_length=48)] = None,
    research: bool | None = None,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    return await svc.list_collections(
        db, viewer, sort=sort, tag=tag, research=research, cursor=cursor, limit=limit
    )


@router.get("/collections/{call_number}", response_model=CollectionOut)
async def get_collection(call_number: str, db: DB, viewer: OptionalUser):
    item = await svc.base.load_item(db, Collection, call_number=call_number.upper())
    item = not_found_unless_visible(viewer, item)
    return (await svc.present(db, viewer, [item]))[0]  # type: ignore[list-item]


@router.post(
    "/collections",
    status_code=201,
    response_model=CollectionOut,
    dependencies=[Depends(limit_write)],
)
async def create_collection(body: CollectionIn, db: DB, user: VerifiedUser):
    item = await svc.create(db, user, body)
    await db.commit()
    return (await svc.present(db, user, [item]))[0]


@router.patch(
    "/collections/{item_id}",
    response_model=CollectionOut,
    dependencies=[Depends(limit_write)],
)
async def update_collection(
    item_id: uuid.UUID, body: CollectionPatch, db: DB, user: ActiveUser
):
    item = await svc.base.load_item(db, Collection, id=item_id)
    if item is None or not (
        item.status == ContentStatus.published or can_manage(user, item)
    ):
        raise NotFound("Not found.")
    if not can_manage(user, item):
        raise Forbidden("Only the author or an admin can edit this.")
    item = await svc.update(db, user, item, body)
    await db.commit()
    return (await svc.present(db, user, [item]))[0]
