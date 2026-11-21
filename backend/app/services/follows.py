"""Followed tags and the "For you" feed."""

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, NotFound
from app.models.content import ContentItem, ContentTag, Tag
from app.models.library import TagFollow
from app.models.user import User
from app.schemas.common import Page
from app.schemas.library import FollowedTag, ItemCard
from app.services.cards import card_page, published_cards

MAX_FOLLOWS = 50


async def _tag(db: AsyncSession, slug: str) -> Tag:
    tag = (await db.execute(select(Tag).where(Tag.slug == slug))).scalar_one_or_none()
    if tag is None:
        raise NotFound("No such tag.")
    return tag


async def set_follow(db: AsyncSession, user: User, slug: str, on: bool) -> bool:
    tag = await _tag(db, slug)
    if on:
        n = await db.scalar(select(func.count()).where(TagFollow.user_id == user.id))
        already = await db.get(TagFollow, (user.id, tag.id))
        if not already and n >= MAX_FOLLOWS:
            raise AppError(
                f"You can follow up to {MAX_FOLLOWS} tags.",
                code="follow_limit",
                status_code=409,
            )
        await db.execute(
            pg_insert(TagFollow)
            .values(user_id=user.id, tag_id=tag.id)
            .on_conflict_do_nothing()
        )
    else:
        await db.execute(
            delete(TagFollow).where(
                TagFollow.user_id == user.id, TagFollow.tag_id == tag.id
            )
        )
    return on


async def followed(db: AsyncSession, user: User) -> list[FollowedTag]:
    rows = await db.execute(
        select(Tag.name, Tag.slug)
        .join(TagFollow, TagFollow.tag_id == Tag.id)
        .where(TagFollow.user_id == user.id)
        .order_by(Tag.slug)
        .limit(MAX_FOLLOWS)
    )
    return [FollowedTag(name=r.name, slug=r.slug) for r in rows]


async def for_you(
    db: AsyncSession, user: User, cursor: str | None, limit: int
) -> Page[ItemCard]:
    """Newest published items carrying any followed tag (never your own posts)."""
    mine = select(TagFollow.tag_id).where(TagFollow.user_id == user.id)
    stmt = published_cards().where(
        ContentItem.author_id != user.id,
        ContentItem.id.in_(
            select(ContentTag.item_id).where(ContentTag.tag_id.in_(mine))
        ),
    )
    return await card_page(db, stmt, ContentItem.created_at, cursor, limit)
