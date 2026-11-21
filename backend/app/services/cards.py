"""Cursor-paged lists of `ItemCard`s over any filter; answers never appear (they live on questions)."""

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ContentItem, ContentStatus
from app.schemas.common import Page, parse_ts_cursor, ts_cursor
from app.schemas.library import ItemCard


def published_cards():
    return select(ContentItem).where(
        ContentItem.status == ContentStatus.published.value,
        ContentItem.type != "answer",
    )


async def card_page(
    db: AsyncSession,
    stmt,
    ts_col,
    cursor: str | None,
    limit: int,
) -> Page[ItemCard]:
    """Newest-first by `ts_col` (the item's own `created_at`, or a join table's timestamp), id as tiebreak."""
    stmt = stmt.add_columns(ts_col.label("ts"))
    if cursor:
        ts, last_id = parse_ts_cursor(cursor)
        stmt = stmt.where(tuple_(ts_col, ContentItem.id) < tuple_(ts, last_id))
    rows = (
        await db.execute(
            stmt.order_by(ts_col.desc(), ContentItem.id.desc()).limit(limit + 1)
        )
    ).all()
    nxt = None
    if len(rows) > limit:
        rows = rows[:limit]
        nxt = ts_cursor(rows[-1].ts, rows[-1][0].id)
    return Page(
        items=[ItemCard.model_validate(r[0], from_attributes=True) for r in rows],
        next_cursor=nxt,
    )
