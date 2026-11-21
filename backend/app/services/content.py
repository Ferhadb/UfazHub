"""Content queries and writes shared by every content type."""

import re
import unicodedata
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, text, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, Forbidden, NotFound
from app.core.jobs import enqueue
from app.core.urls import canonical_url
from app.models.content import (
    CALL_PREFIX,
    Bookmark,
    ContentItem,
    ContentStatus,
    ContentTag,
    ContentType,
    Resource,
    ResourceLink,
    Tag,
    Vote,
)
from app.models.user import User
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.content import (
    BookmarkOut,
    DuplicateHit,
    LinkIn,
    ResourceIn,
    ResourceOut,
    ResourcePatch,
    TagOut,
    VoteOut,
)
from app.services import audit
from app.services.uploads import owned_attachment

# --- helpers -----------------------------------------------------------------------


def slugify(name: str) -> str:
    folded = unicodedata.normalize("NFKC", name).casefold()
    return re.sub(r"[\W_]+", "-", folded).strip("-")[:48]


async def _call_number(db: AsyncSession, type_: ContentType) -> str:
    n = (
        await db.execute(text(f"SELECT nextval('call_seq_{type_.value}')"))
    ).scalar_one()
    return f"{CALL_PREFIX[type_]}-{n:04d}"


async def _tags(db: AsyncSession, names: list[str]) -> list[Tag]:
    wanted: dict[str, str] = {}
    for raw in names:
        name = " ".join(raw.split())[:40]
        if slug := slugify(name):
            wanted.setdefault(slug, name)
    if not wanted:
        return []
    await db.execute(
        pg_insert(Tag)
        .values([{"id": uuid.uuid4(), "name": n, "slug": s} for s, n in wanted.items()])
        .on_conflict_do_nothing(index_elements=["slug"])
    )
    return list(
        (await db.execute(select(Tag).where(Tag.slug.in_(wanted)).order_by(Tag.slug)))
        .scalars()
        .all()
    )


def _links(existing: list[ResourceLink], new: list[LinkIn]) -> list[ResourceLink]:
    """Reuse rows whose canonical URL is kept (the unique constraint forbids delete+insert in one flush)."""
    by_canon = {link.canonical_url: link for link in existing}
    out: dict[str, ResourceLink] = {}
    for pos, item in enumerate(new):
        canon = canonical_url(item.url)
        if canon in out:
            continue
        link = by_canon.get(canon) or ResourceLink(canonical_url=canon)
        link.url, link.label, link.position = item.url, item.label, pos
        out[canon] = link
    return list(out.values())


async def load_item[T: ContentItem](
    db: AsyncSession, model: type[T], **where: Any
) -> T | None:
    stmt = select(model).execution_options(populate_existing=True)
    for col, val in where.items():
        stmt = stmt.where(getattr(model, col) == val)
    return (await db.execute(stmt)).scalar_one_or_none()


async def load_resource(db: AsyncSession, **where: Any) -> Resource | None:
    return await load_item(db, Resource, **where)


async def viewer_state(
    db: AsyncSession, user: User | None, ids: list[uuid.UUID]
) -> tuple[dict[uuid.UUID, int], set[uuid.UUID]]:
    if user is None or not ids:
        return {}, set()
    votes = await db.execute(
        select(Vote.item_id, Vote.value).where(
            Vote.user_id == user.id, Vote.item_id.in_(ids)
        )
    )
    marks = await db.execute(
        select(Bookmark.item_id).where(
            Bookmark.user_id == user.id, Bookmark.item_id.in_(ids)
        )
    )
    return {i: v for i, v in votes.all()}, {i for (i,) in marks.all()}


def decorate[T](
    out: T,
    item: ContentItem,
    viewer: User | None,
    votes: dict[uuid.UUID, int],
    marks: set[uuid.UUID],
) -> T:
    """Fill the per-viewer fields of any content `*Out` (vote, bookmark, moderation reason)."""
    # The moderation reason is for the author and admins only.
    if viewer is None or (viewer.id != item.author_id and viewer.role != "admin"):
        out.hidden_reason = None  # type: ignore[attr-defined]
    out.my_vote = votes.get(item.id, 0)  # type: ignore[attr-defined]
    out.bookmarked = item.id in marks  # type: ignore[attr-defined]
    return out


def to_out(
    item: Resource,
    viewer: User | None,
    votes: dict[uuid.UUID, int],
    marks: set[uuid.UUID],
) -> ResourceOut:
    out = ResourceOut.model_validate(item, from_attributes=True)
    return decorate(out, item, viewer, votes, marks)


async def present(
    db: AsyncSession, viewer: User | None, items: list[Resource]
) -> list[ResourceOut]:
    votes, marks = await viewer_state(db, viewer, [i.id for i in items])
    return [to_out(i, viewer, votes, marks) for i in items]


# --- resources ---------------------------------------------------------------------


async def create_resource(
    db: AsyncSession, user: User, data: ResourceIn, status: str
) -> Resource:
    fields = data.model_dump(exclude={"links", "tags", "primary_attachment_id"})
    if data.primary_attachment_id:
        await owned_attachment(db, user, data.primary_attachment_id, None)
    item = Resource(
        primary_attachment_id=data.primary_attachment_id,
        **fields,
        id=uuid.uuid4(),
        author_id=user.id,
        author=user,
        status=status,
        call_number=await _call_number(db, ContentType.resource),
        links=_links([], data.links),
        tags=await _tags(db, data.tags),
    )
    db.add(item)
    await db.flush()
    return await load_resource(db, id=item.id)  # type: ignore[return-value]


async def update_resource(
    db: AsyncSession, actor: User, item: Resource, data: ResourcePatch
) -> Resource:
    changes = data.model_dump(exclude_unset=True, exclude={"links", "tags"})
    if changes.get("primary_attachment_id"):
        await owned_attachment(db, actor, changes["primary_attachment_id"], None)
    before = {k: getattr(item, k) for k in changes}
    for k, v in changes.items():
        if v is None and k not in ("time_commitment_minutes", "primary_attachment_id"):
            raise AppError(f"{k} cannot be empty", fields={k: "Required"})
        setattr(item, k, v)
    if data.links is not None:
        item.links = _links(item.links, data.links)
    if data.tags is not None:
        item.tags = await _tags(db, data.tags)
    item.updated_at = func.now()  # type: ignore[assignment]
    if actor.id != item.author_id:
        await audit.record(
            db,
            actor_id=actor.id,
            action="content.edit",
            target_type="content_item",
            target_id=item.id,
            before=before,
            after=changes,
        )
    await db.flush()
    return await load_resource(db, id=item.id)  # type: ignore[return-value]


async def keyset_page[T: ContentItem](
    db: AsyncSession, stmt, model: type[T], sort: str, cursor: str | None, limit: int
) -> tuple[list[T], str | None]:
    """Newest-first (or top-first) keyset pagination over any content subtype."""
    keys = [model.created_at, model.id]
    if sort == "top":
        keys.insert(0, model.vote_score)
    if cursor:
        raw = decode_cursor(cursor).get("k")
        try:
            if not isinstance(raw, list) or len(raw) != len(keys):
                raise ValueError
            if sort == "top" and not isinstance(raw[0], int):
                raise ValueError
            vals = [*raw[:-2], datetime.fromisoformat(raw[-2]), uuid.UUID(raw[-1])]
        except (TypeError, ValueError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
        stmt = stmt.where(tuple_(*keys) < tuple_(*vals))
    rows = list(
        (await db.execute(stmt.order_by(*[k.desc() for k in keys]).limit(limit + 1)))
        .scalars()
        .all()
    )
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        k = [last.created_at.isoformat(), str(last.id)]
        nxt = encode_cursor({"k": [last.vote_score, *k] if sort == "top" else k})
    return rows, nxt


async def list_resources(
    db: AsyncSession,
    viewer: User | None,
    *,
    sort: str,
    tag: str | None,
    difficulty: str | None,
    research: bool | None,
    cursor: str | None,
    limit: int,
) -> Page[ResourceOut]:
    stmt = select(Resource).where(Resource.status == ContentStatus.published.value)
    if tag:
        stmt = stmt.where(Resource.tags.any(Tag.slug == tag))
    if difficulty:
        stmt = stmt.where(Resource.difficulty == difficulty)
    if research is not None:
        stmt = stmt.where(Resource.is_research.is_(research))
    rows, nxt = await keyset_page(db, stmt, Resource, sort, cursor, limit)
    return Page(items=await present(db, viewer, rows), next_cursor=nxt)


# --- moderation (hide / publish) ------------------------------------------------------


async def set_status(
    db: AsyncSession,
    actor: User,
    item_id: uuid.UUID,
    status: ContentStatus,
    reason: str | None,
) -> None:
    item = await db.get(ContentItem, item_id)
    if item is None:
        raise NotFound("Not found.")
    before = {"status": item.status, "hidden_reason": item.hidden_reason}
    item.status = status.value
    item.hidden_reason = reason
    await audit.record(
        db,
        actor_id=actor.id,
        action=f"content.{'hide' if reason else 'publish'}",
        target_type="content_item",
        target_id=item.id,
        before=before,
        after={"status": item.status, "hidden_reason": reason},
        reason=reason,
    )
    await db.flush()


# --- votes and bookmarks -----------------------------------------------------------------


async def _lock_visible(
    db: AsyncSession, item_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    """Lock the item row (serialises concurrent votes on it) and return (id, author_id)."""
    row = (
        await db.execute(
            select(ContentItem.id, ContentItem.author_id)
            .where(
                ContentItem.id == item_id,
                ContentItem.status == ContentStatus.published.value,
            )
            .with_for_update()
        )
    ).one_or_none()
    if row is None:
        raise NotFound("Not found.")
    return row.id, row.author_id


async def cast_vote(
    db: AsyncSession, user: User, item_id: uuid.UUID, value: int
) -> VoteOut:
    """Write the vote and adjust `vote_score` in one transaction, under the item's row lock."""
    _, author_id = await _lock_visible(db, item_id)
    if author_id == user.id:
        raise Forbidden("You cannot vote on your own post.", code="self_vote")
    old = (
        await db.execute(
            select(Vote.value).where(Vote.user_id == user.id, Vote.item_id == item_id)
        )
    ).scalar_one_or_none() or 0
    if value != old:
        if value == 0:
            await db.execute(
                delete(Vote).where(Vote.user_id == user.id, Vote.item_id == item_id)
            )
        else:
            used = (
                await db.execute(
                    select(func.count())
                    .select_from(Vote)
                    .where(
                        Vote.user_id == user.id,
                        Vote.updated_at > func.now() - text("interval '1 day'"),
                    )
                )
            ).scalar_one()
            if used >= settings.VOTE_DAILY_CAP:
                raise AppError(
                    "Daily vote limit reached. Come back tomorrow.",
                    code="vote_cap_reached",
                    status_code=429,
                    headers={"Retry-After": "3600"},
                )
            await db.execute(
                pg_insert(Vote)
                .values(user_id=user.id, item_id=item_id, value=value)
                .on_conflict_do_update(
                    index_elements=["user_id", "item_id"],
                    set_={"value": value, "updated_at": func.now()},
                )
            )
    score = (
        await db.execute(
            update(ContentItem)
            .where(ContentItem.id == item_id)
            .values(vote_score=ContentItem.vote_score + (value - old))
            .returning(ContentItem.vote_score)
        )
    ).scalar_one()
    return VoteOut(vote_score=score, my_vote=value)  # type: ignore[arg-type]


async def set_bookmark(
    db: AsyncSession, user: User, item_id: uuid.UUID, on: bool
) -> BookmarkOut:
    """Idempotent. Only the request that actually inserts/deletes the row moves the counter."""
    visible = await db.scalar(
        select(ContentItem.id).where(
            ContentItem.id == item_id,
            ContentItem.status == ContentStatus.published.value,
        )
    )
    if visible is None and on:
        raise NotFound("Not found.")
    if on:
        changed = await db.execute(
            pg_insert(Bookmark)
            .values(user_id=user.id, item_id=item_id)
            .on_conflict_do_nothing()
            .returning(Bookmark.item_id)
        )
    else:
        changed = await db.execute(
            delete(Bookmark)
            .where(Bookmark.user_id == user.id, Bookmark.item_id == item_id)
            .returning(Bookmark.item_id)
        )
    delta = (1 if on else -1) if changed.first() else 0
    count = (
        await db.execute(
            update(ContentItem)
            .where(ContentItem.id == item_id)
            .values(bookmark_count=ContentItem.bookmark_count + delta)
            .returning(ContentItem.bookmark_count)
        )
    ).scalar_one_or_none()
    if count is None:
        raise NotFound("Not found.")
    return BookmarkOut(bookmark_count=count, bookmarked=on)


# --- tags and duplicates --------------------------------------------------------------------


async def popular_tags(db: AsyncSession, prefix: str, limit: int) -> list[TagOut]:
    n = func.count(ContentItem.id)
    stmt = (
        select(Tag.name, Tag.slug, n.label("n"))
        .join(ContentTag, ContentTag.tag_id == Tag.id)
        .join(
            ContentItem,
            (ContentItem.id == ContentTag.item_id)
            & (ContentItem.status == ContentStatus.published.value),
        )
        .group_by(Tag.id)
        .order_by(n.desc(), Tag.slug)
        .limit(limit)
    )
    if prefix:
        stmt = stmt.where(Tag.slug.startswith(slugify(prefix), autoescape=True))
    return [
        TagOut(name=r.name, slug=r.slug, count=r.n) for r in (await db.execute(stmt))
    ]


async def find_duplicates(
    db: AsyncSession, url: str | None, title: str | None
) -> list[DuplicateHit]:
    hits: dict[str, DuplicateHit] = {}
    if url:
        try:
            canon = canonical_url(url)
        except ValueError as exc:
            raise AppError(str(exc), fields={"url": str(exc)}) from exc
        rows = await db.execute(
            select(ContentItem.call_number, ContentItem.title)
            .join(ResourceLink, ResourceLink.resource_id == ContentItem.id)
            .where(
                ResourceLink.canonical_url == canon,
                ContentItem.status == ContentStatus.published.value,
            )
            .limit(5)
        )
        for r in rows:
            hits[r.call_number] = DuplicateHit(
                call_number=r.call_number, title=r.title, match="same_link"
            )
    if title and len(title.strip()) >= 3:
        await db.execute(
            text("SELECT set_config('pg_trgm.similarity_threshold', '0.5', true)")
        )
        rows = await db.execute(
            text(
                "SELECT call_number, title FROM content_items "
                "WHERE status = 'published' AND type = 'resource' "
                "AND f_unaccent(lower(title)) % f_unaccent(lower(:t)) "
                "ORDER BY similarity(f_unaccent(lower(title)), f_unaccent(lower(:t))) DESC LIMIT 5"
            ),
            {"t": title.strip()},
        )
        for r in rows:
            hits.setdefault(
                r.call_number,
                DuplicateHit(
                    call_number=r.call_number, title=r.title, match="similar_title"
                ),
            )
    return list(hits.values())


async def queue_previews(item: Resource) -> None:
    """Ask the worker for previews of links that have none yet (call after the commit)."""
    for link in item.links:
        if link.preview_fetched_at is None:
            await enqueue("fetch_link_preview", str(link.id))
