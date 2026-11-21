"""Research listing, followed tags and the For-you feed, bookmarks, reading lists, broken links."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, CurrentUser
from app.api.permissions import ActiveUser
from app.core.ratelimit import limit_search, limit_vote, limit_write
from app.models.content import ContentItem, Tag
from app.schemas.common import Page
from app.schemas.content import LinkOut
from app.schemas.library import (
    FollowedTag,
    FollowOut,
    ItemCard,
    ListIn,
    ReadingListOut,
    SharedList,
)
from app.services import follows, linkhealth, readinglists
from app.services.cards import card_page, published_cards

router = APIRouter(tags=["library"])

Cursor = Annotated[str | None, Query(max_length=512)]
Limit = Annotated[int, Query(ge=1, le=50)]


@router.get("/research", response_model=Page[ItemCard])
async def research(
    db: DB,
    type: Literal["resource", "article", "collection", "question"] | None = None,
    tag: Annotated[str | None, Query(max_length=48)] = None,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    """Everything flagged as research, across content types."""
    stmt = published_cards().where(ContentItem.is_research.is_(True))
    if type:
        stmt = stmt.where(ContentItem.type == type)
    if tag:
        stmt = stmt.where(ContentItem.tags.any(Tag.slug == tag))
    return await card_page(db, stmt, ContentItem.created_at, cursor, limit)


# --- follows and the For-you feed -----------------------------------------------------
@router.put(
    "/tags/{slug}/follow", response_model=FollowOut, dependencies=[Depends(limit_vote)]
)
async def follow(slug: str, db: DB, user: ActiveUser):
    out = FollowOut(following=await follows.set_follow(db, user, slug, True))
    await db.commit()
    return out


@router.delete(
    "/tags/{slug}/follow", response_model=FollowOut, dependencies=[Depends(limit_vote)]
)
async def unfollow(slug: str, db: DB, user: ActiveUser):
    out = FollowOut(following=await follows.set_follow(db, user, slug, False))
    await db.commit()
    return out


@router.get("/me/tags", response_model=list[FollowedTag])
async def my_tags(db: DB, user: CurrentUser):
    """Followed tags, capped at 50, so not paged."""
    return await follows.followed(db, user)


@router.get(
    "/feed/for-you", response_model=Page[ItemCard], dependencies=[Depends(limit_search)]
)
async def for_you(db: DB, user: CurrentUser, cursor: Cursor = None, limit: Limit = 20):
    return await follows.for_you(db, user, cursor, limit)


# --- bookmarks and reading lists ---------------------------------------------------------
@router.get("/me/bookmarks", response_model=Page[ItemCard])
async def my_bookmarks(
    db: DB, user: CurrentUser, cursor: Cursor = None, limit: Limit = 20
):
    return await readinglists.bookmarks(db, user, cursor, limit)


@router.get("/me/reading-lists", response_model=Page[ReadingListOut])
async def my_lists(db: DB, user: CurrentUser):
    """Capped at 30 per person, so there is no next page."""
    return Page(items=await readinglists.my_lists(db, user))


@router.post(
    "/me/reading-lists",
    status_code=201,
    response_model=ReadingListOut,
    dependencies=[Depends(limit_write)],
)
async def create_list(body: ListIn, db: DB, user: ActiveUser):
    out = await readinglists.create(db, user, body)
    await db.commit()
    return out


@router.patch(
    "/reading-lists/{list_id}",
    response_model=ReadingListOut,
    dependencies=[Depends(limit_write)],
)
async def rename_list(list_id: uuid.UUID, body: ListIn, db: DB, user: ActiveUser):
    out = await readinglists.rename(db, user, list_id, body)
    await db.commit()
    return out


@router.delete(
    "/reading-lists/{list_id}", status_code=204, dependencies=[Depends(limit_write)]
)
async def delete_list(list_id: uuid.UUID, db: DB, user: ActiveUser):
    await readinglists.delete_list(db, user, list_id)
    await db.commit()


@router.get("/reading-lists/{list_id}/items", response_model=Page[ItemCard])
async def list_items(
    list_id: uuid.UUID,
    db: DB,
    user: CurrentUser,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    rl = await readinglists.owned(db, user, list_id)
    return await readinglists.items(db, rl, cursor, limit)


@router.put(
    "/reading-lists/{list_id}/items/{item_id}",
    response_model=ReadingListOut,
    dependencies=[Depends(limit_vote)],
)
async def add_to_list(list_id: uuid.UUID, item_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await readinglists.set_item(db, user, list_id, item_id, True)
    await db.commit()
    return out


@router.delete(
    "/reading-lists/{list_id}/items/{item_id}",
    response_model=ReadingListOut,
    dependencies=[Depends(limit_vote)],
)
async def remove_from_list(
    list_id: uuid.UUID, item_id: uuid.UUID, db: DB, user: ActiveUser
):
    out = await readinglists.set_item(db, user, list_id, item_id, False)
    await db.commit()
    return out


@router.put(
    "/reading-lists/{list_id}/share",
    response_model=ReadingListOut,
    dependencies=[Depends(limit_write)],
)
async def share_list(list_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await readinglists.set_shared(db, user, list_id, True)
    await db.commit()
    return out


@router.delete(
    "/reading-lists/{list_id}/share",
    response_model=ReadingListOut,
    dependencies=[Depends(limit_write)],
)
async def unshare_list(list_id: uuid.UUID, db: DB, user: ActiveUser):
    out = await readinglists.set_shared(db, user, list_id, False)
    await db.commit()
    return out


@router.get(
    "/shared/lists/{token}",
    response_model=SharedList,
    dependencies=[Depends(limit_search)],
)
async def shared_list(
    token: str,
    db: DB,
    cursor: Cursor = None,
    limit: Limit = 20,
):
    return await readinglists.shared(db, token, cursor, limit)


# --- link health -----------------------------------------------------------------------
@router.put(
    "/links/{link_id}/broken",
    response_model=LinkOut,
    dependencies=[Depends(limit_write)],
)
async def report_broken(link_id: uuid.UUID, db: DB, user: ActiveUser):
    link = await linkhealth.report_broken(db, link_id)
    await db.commit()
    return link
