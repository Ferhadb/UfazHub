"""Collections: an ordered shelf of published resources and articles, each with its own note."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.permissions import initial_status
from app.core.errors import AppError
from app.models.content import (
    Collection,
    CollectionItem,
    ContentItem,
    ContentStatus,
    ContentType,
    Tag,
)
from app.models.user import User
from app.schemas.collections import (
    CollectionIn,
    CollectionItemIn,
    CollectionItemOut,
    CollectionOut,
    CollectionPatch,
)
from app.schemas.common import Page
from app.services import audit
from app.services import content as base

SHELVABLE = (ContentType.resource.value, ContentType.article.value)


async def _items(
    db: AsyncSession, wanted: list[CollectionItemIn], existing: list[CollectionItem]
) -> list[CollectionItem]:
    ids = [w.item_id for w in wanted]
    if len(set(ids)) != len(ids):
        raise AppError(
            "An item can only be on the shelf once.", fields={"items": "Duplicate item"}
        )
    found = {
        i.id: i
        for i in (
            await db.execute(
                select(ContentItem).where(
                    ContentItem.id.in_(ids),
                    ContentItem.type.in_(SHELVABLE),
                    ContentItem.status == ContentStatus.published.value,
                )
            )
        ).scalars()
    }
    missing = [i for i in ids if i not in found]
    if missing:
        raise AppError(
            "Only published resources and articles can go on a shelf.",
            code="invalid_item",
            status_code=422,
            fields={"items": f"Unavailable: {', '.join(str(m) for m in missing)}"},
        )
    # Reuse rows for kept items (the unique constraint forbids delete + insert in one flush).
    kept = {row.item_id: row for row in existing}
    out = []
    for pos, w in enumerate(wanted):
        row = kept.get(w.item_id) or CollectionItem(item_id=w.item_id)
        row.item, row.position, row.note = found[w.item_id], pos, w.note
        out.append(row)
    return out


async def create(db: AsyncSession, user: User, data: CollectionIn) -> Collection:
    item = Collection(
        id=uuid.uuid4(),
        author_id=user.id,
        author=user,
        status=initial_status(user),
        call_number=await base._call_number(db, ContentType.collection),
        title=data.title,
        description=data.description,
        is_research=data.is_research,
        tags=await base._tags(db, data.tags),
        items=await _items(db, data.items, []),
    )
    db.add(item)
    await db.flush()
    return await base.load_item(db, Collection, id=item.id)  # type: ignore[return-value]


async def update(
    db: AsyncSession, actor: User, item: Collection, data: CollectionPatch
) -> Collection:
    changes = data.model_dump(exclude_unset=True, exclude={"tags", "items"})
    for k, v in changes.items():
        if v is None and k != "description":
            raise AppError(f"{k} cannot be empty", fields={k: "Required"})
    before = {k: getattr(item, k) for k in changes}
    for k, v in changes.items():
        setattr(item, k, v)
    if data.tags is not None:
        item.tags = await base._tags(db, data.tags)
    if data.items is not None:
        item.items = await _items(db, data.items, item.items)
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
    return await base.load_item(db, Collection, id=item.id)  # type: ignore[return-value]


async def present(
    db: AsyncSession, viewer: User | None, items: list[Collection]
) -> list[CollectionOut]:
    votes, marks = await base.viewer_state(db, viewer, [i.id for i in items])
    out = []
    for c in items:
        o = CollectionOut.model_validate(c, from_attributes=True)
        # Items hidden or unpublished after being shelved quietly drop off the shelf.
        shown = [r for r in c.items if r.item.status == ContentStatus.published]
        o.items = [
            CollectionItemOut.model_validate(r, from_attributes=True) for r in shown
        ]
        out.append(base.decorate(o, c, viewer, votes, marks))
    return out


async def list_collections(
    db: AsyncSession,
    viewer: User | None,
    *,
    sort: str,
    tag: str | None,
    research: bool | None,
    cursor: str | None,
    limit: int,
) -> Page[CollectionOut]:
    stmt = select(Collection).where(Collection.status == ContentStatus.published.value)
    if tag:
        stmt = stmt.where(Collection.tags.any(Tag.slug == tag))
    if research is not None:
        stmt = stmt.where(Collection.is_research.is_(research))
    rows, nxt = await base.keyset_page(db, stmt, Collection, sort, cursor, limit)
    return Page(items=await present(db, viewer, rows), next_cursor=nxt)
