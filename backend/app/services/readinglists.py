"""Bookmarks as a list, and named reading lists (private unless shared by link)."""

import secrets
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound
from app.models.content import Bookmark, ContentItem, ContentStatus
from app.models.library import ReadingList, ReadingListItem
from app.models.user import User
from app.schemas.common import Page
from app.schemas.content import AuthorOut
from app.schemas.library import ItemCard, ListIn, ReadingListOut, SharedList
from app.services.cards import card_page, published_cards

MAX_LISTS = 30
MAX_ITEMS = 200


async def bookmarks(
    db: AsyncSession, user: User, cursor: str | None, limit: int
) -> Page[ItemCard]:
    stmt = published_cards().join(
        Bookmark, (Bookmark.item_id == ContentItem.id) & (Bookmark.user_id == user.id)
    )
    return await card_page(db, stmt, Bookmark.created_at, cursor, limit)


async def _out(db: AsyncSession, rl: ReadingList) -> ReadingListOut:
    n = await db.scalar(select(func.count()).where(ReadingListItem.list_id == rl.id))
    return ReadingListOut(
        id=rl.id,
        name=rl.name,
        share_token=rl.share_token,
        item_count=n or 0,
        created_at=rl.created_at,
    )


async def owned(db: AsyncSession, user: User, list_id: uuid.UUID) -> ReadingList:
    """Someone else's list looks exactly like a missing one."""
    rl = await db.get(ReadingList, list_id)
    if rl is None or rl.owner_id != user.id:
        raise NotFound("No such list.")
    return rl


async def my_lists(db: AsyncSession, user: User) -> list[ReadingListOut]:
    rows = (
        (
            await db.execute(
                select(ReadingList)
                .where(ReadingList.owner_id == user.id)
                .order_by(ReadingList.created_at.desc(), ReadingList.id.desc())
                .limit(MAX_LISTS)
            )
        )
        .scalars()
        .all()
    )
    return [await _out(db, rl) for rl in rows]


async def create(db: AsyncSession, user: User, data: ListIn) -> ReadingListOut:
    n = await db.scalar(select(func.count()).where(ReadingList.owner_id == user.id))
    if n >= MAX_LISTS:
        raise AppError(
            f"You can keep up to {MAX_LISTS} lists.", code="list_limit", status_code=409
        )
    rl = ReadingList(owner_id=user.id, name=data.name)
    db.add(rl)
    await db.flush()
    await db.refresh(rl)
    return await _out(db, rl)


async def rename(
    db: AsyncSession, user: User, list_id: uuid.UUID, data: ListIn
) -> ReadingListOut:
    rl = await owned(db, user, list_id)
    rl.name = data.name
    await db.flush()
    return await _out(db, rl)


async def delete_list(db: AsyncSession, user: User, list_id: uuid.UUID) -> None:
    await db.delete(await owned(db, user, list_id))


async def set_item(
    db: AsyncSession, user: User, list_id: uuid.UUID, item_id: uuid.UUID, on: bool
) -> ReadingListOut:
    rl = await owned(db, user, list_id)
    if on:
        visible = await db.scalar(
            select(ContentItem.id).where(
                ContentItem.id == item_id,
                ContentItem.status == ContentStatus.published.value,
                ContentItem.type != "answer",
            )
        )
        if visible is None:
            raise NotFound("Not found.")
        have = await db.get(ReadingListItem, (rl.id, item_id))
        n = await db.scalar(
            select(func.count()).where(ReadingListItem.list_id == rl.id)
        )
        if not have and n >= MAX_ITEMS:
            raise AppError(
                f"A list holds up to {MAX_ITEMS} items.",
                code="list_full",
                status_code=409,
            )
        await db.execute(
            pg_insert(ReadingListItem)
            .values(list_id=rl.id, item_id=item_id)
            .on_conflict_do_nothing()
        )
    else:
        await db.execute(
            delete(ReadingListItem).where(
                ReadingListItem.list_id == rl.id, ReadingListItem.item_id == item_id
            )
        )
    return await _out(db, rl)


async def items(
    db: AsyncSession, rl: ReadingList, cursor: str | None, limit: int
) -> Page[ItemCard]:
    stmt = published_cards().join(
        ReadingListItem,
        (ReadingListItem.item_id == ContentItem.id)
        & (ReadingListItem.list_id == rl.id),
    )
    return await card_page(db, stmt, ReadingListItem.added_at, cursor, limit)


async def set_shared(
    db: AsyncSession, user: User, list_id: uuid.UUID, on: bool
) -> ReadingListOut:
    rl = await owned(db, user, list_id)
    if on and rl.share_token is None:
        rl.share_token = secrets.token_urlsafe(16)
    elif not on:
        rl.share_token = None
    await db.flush()
    return await _out(db, rl)


async def shared(
    db: AsyncSession, token: str, cursor: str | None, limit: int
) -> SharedList:
    rl = (
        await db.execute(select(ReadingList).where(ReadingList.share_token == token))
    ).scalar_one_or_none()
    if rl is None:
        raise NotFound("This list is private or does not exist.")
    owner = await db.get(User, rl.owner_id)
    page = await items(db, rl, cursor, limit)
    return SharedList(
        name=rl.name,
        owner=AuthorOut.model_validate(owner, from_attributes=True),
        items=page.items,
        next_cursor=page.next_cursor,
    )
