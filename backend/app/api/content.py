import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB
from app.api.permissions import (
    ActiveUser,
    AdminUser,
    OptionalUser,
    VerifiedUser,
    can_manage,
    initial_status,
    not_found_unless_visible,
)
from app.core.errors import Forbidden, NotFound
from app.core.ratelimit import limit_search, limit_vote, limit_write
from app.models.content import ContentStatus
from app.schemas.common import Page
from app.schemas.content import (
    BookmarkOut,
    DuplicateHit,
    HideIn,
    ResourceIn,
    ResourceOut,
    ResourcePatch,
    SearchHit,
    TagOut,
    VoteIn,
    VoteOut,
)
from app.services import content as svc
from app.services import search as search_svc

router = APIRouter(tags=["content"])

Limit = Annotated[int, Query(ge=1, le=50)]
Difficulty = Literal["beginner", "intermediate", "advanced"]


# --- reading (public) --------------------------------------------------------------------
@router.get("/resources", response_model=Page[ResourceOut])
async def list_resources(
    db: DB,
    viewer: OptionalUser,
    sort: Literal["latest", "top"] = "latest",
    tag: Annotated[str | None, Query(max_length=48)] = None,
    difficulty: Difficulty | None = None,
    research: bool | None = None,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Limit = 20,
):
    return await svc.list_resources(
        db,
        viewer,
        sort=sort,
        tag=tag,
        difficulty=difficulty,
        research=research,
        cursor=cursor,
        limit=limit,
    )


@router.get(
    "/resources/duplicates",
    response_model=list[DuplicateHit],
    dependencies=[Depends(limit_search)],
)
async def duplicates(
    db: DB,
    url: Annotated[str | None, Query(max_length=2048)] = None,
    title: Annotated[str | None, Query(max_length=200)] = None,
):
    return await svc.find_duplicates(db, url, title)


@router.get("/resources/{call_number}", response_model=ResourceOut)
async def get_resource(call_number: str, db: DB, viewer: OptionalUser):
    item = await svc.load_resource(db, call_number=call_number.upper())
    item = not_found_unless_visible(viewer, item)
    return (await svc.present(db, viewer, [item]))[0]  # type: ignore[list-item]


@router.get("/tags", response_model=Page[TagOut])
async def tags(db: DB, q: Annotated[str, Query(max_length=40)] = "", limit: Limit = 20):
    """Most used tags first; bounded top-N, so there is never a next page."""
    return Page(items=await svc.popular_tags(db, q, limit))


@router.get(
    "/search", response_model=Page[SearchHit], dependencies=[Depends(limit_search)]
)
async def search(
    db: DB,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    type: Literal["resource", "article", "collection", "question"] | None = None,
    tag: Annotated[str | None, Query(max_length=48)] = None,
    research: bool | None = None,
    difficulty: Difficulty | None = None,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
    limit: Limit = 10,
):
    return await search_svc.search(
        db,
        q.strip(),
        type=type,
        tag=tag,
        research=research,
        difficulty=difficulty,
        cursor=cursor,
        limit=limit,
    )


# --- writing ---------------------------------------------------------------------------------
@router.post(
    "/resources",
    status_code=201,
    response_model=ResourceOut,
    dependencies=[Depends(limit_write)],
)
async def create_resource(body: ResourceIn, db: DB, user: VerifiedUser):
    item = await svc.create_resource(db, user, body, initial_status(user))
    await db.commit()
    return (await svc.present(db, user, [item]))[0]


@router.patch(
    "/resources/{item_id}",
    response_model=ResourceOut,
    dependencies=[Depends(limit_write)],
)
async def update_resource(
    item_id: uuid.UUID, body: ResourcePatch, db: DB, user: ActiveUser
):
    item = await svc.load_resource(db, id=item_id)
    if item is None or not (
        item.status == ContentStatus.published or can_manage(user, item)
    ):
        raise NotFound("Not found.")
    if not can_manage(user, item):
        raise Forbidden("Only the author or an admin can edit this.")
    item = await svc.update_resource(db, user, item, body)
    await db.commit()
    return (await svc.present(db, user, [item]))[0]


@router.put(
    "/content/{item_id}/vote",
    response_model=VoteOut,
    dependencies=[Depends(limit_vote)],
)
async def vote(item_id: uuid.UUID, body: VoteIn, db: DB, user: ActiveUser):
    out = await svc.cast_vote(db, user, item_id, body.value)
    await db.commit()
    return out


@router.put(
    "/content/{item_id}/bookmark",
    response_model=BookmarkOut,
    dependencies=[Depends(limit_vote)],
)
async def add_bookmark(item_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await svc.set_bookmark(db, user, item_id, True)
    await db.commit()
    return out


@router.delete(
    "/content/{item_id}/bookmark",
    response_model=BookmarkOut,
    dependencies=[Depends(limit_vote)],
)
async def remove_bookmark(item_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await svc.set_bookmark(db, user, item_id, False)
    await db.commit()
    return out


@router.post(
    "/content/{item_id}/hide", status_code=204, dependencies=[Depends(limit_write)]
)
async def hide(item_id: uuid.UUID, body: HideIn, db: DB, admin: AdminUser):
    await svc.set_status(db, admin, item_id, ContentStatus.hidden, body.reason)
    await db.commit()


@router.post(
    "/content/{item_id}/publish", status_code=204, dependencies=[Depends(limit_write)]
)
async def publish(item_id: uuid.UUID, db: DB, admin: AdminUser):
    """Approve a pending item or restore a hidden one."""
    await svc.set_status(db, admin, item_id, ContentStatus.published, None)
    await db.commit()
