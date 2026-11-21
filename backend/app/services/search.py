"""Unified search across content types.

Ranking = ts_rank_cd over the weighted tsvector (title A, tags B, description C, notes D).
When full-text finds nothing, the query reruns against pg_trgm word similarity on the title,
so typos ("algoritms") still find things. The cursor remembers which mode produced the page.
Highlights use U+0002/U+0003 markers instead of HTML, so the client can never be handed markup.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.schemas.common import Page, decode_cursor, encode_cursor
from app.schemas.content import SearchHit

HL_TITLE = "StartSel=\x02, StopSel=\x03, HighlightAll=true"
HL_SNIPPET = "StartSel=\x02, StopSel=\x03, MaxFragments=1, MaxWords=24, MinWords=8"

SQL = """
WITH q AS (
  SELECT websearch_to_tsquery('ufaz_search', :q) AS tsq, f_unaccent(lower(:q)) AS qn
),
hits AS (
  SELECT ci.id, ci.type, ci.call_number, ci.title, ci.description, ci.is_research,
         ci.vote_score, ci.created_at,
         ts_rank_cd(ci.search_vector, q.tsq, 32)::float8
           + CASE WHEN :fuzzy THEN word_similarity(q.qn, f_unaccent(lower(ci.title)))::float8
                  ELSE 0 END AS rank
  FROM content_items ci, q
  WHERE ci.status = 'published'
    AND (ci.search_vector @@ q.tsq
         OR (:fuzzy AND q.qn <% f_unaccent(lower(ci.title))))
    {filters}
),
page AS (
  SELECT * FROM hits {cursor} ORDER BY rank DESC, id DESC LIMIT :lim
)
SELECT page.id, page.type, page.call_number, page.title, page.is_research, page.vote_score,
       page.created_at, page.rank,
       ts_headline('ufaz_search', page.title, q.tsq, :hl_title) AS title_hl,
       ts_headline('ufaz_search', page.description, q.tsq, :hl_snippet) AS snippet
FROM page, q ORDER BY page.rank DESC, page.id DESC
"""


async def search(
    db: AsyncSession,
    q: str,
    *,
    type: str | None,
    tag: str | None,
    research: bool | None,
    difficulty: str | None,
    cursor: str | None,
    limit: int,
) -> Page[SearchHit]:
    params: dict = {
        "q": q,
        "fuzzy": False,
        "lim": limit + 1,
        "hl_title": HL_TITLE,
        "hl_snippet": HL_SNIPPET,
    }
    filters = []
    if type:
        filters.append("AND ci.type = :type")
        params["type"] = type
    if tag:
        filters.append(
            "AND EXISTS (SELECT 1 FROM content_tags ct JOIN tags t ON t.id = ct.tag_id "
            "WHERE ct.item_id = ci.id AND t.slug = :tag)"
        )
        params["tag"] = tag
    if research is not None:
        filters.append("AND ci.is_research = :research")
        params["research"] = research
    if difficulty:
        filters.append(
            "AND EXISTS (SELECT 1 FROM resources r WHERE r.id = ci.id AND r.difficulty = :difficulty)"
        )
        params["difficulty"] = difficulty
    cursor_sql = ""
    if cursor:
        c = decode_cursor(cursor)
        try:
            params["crank"], params["cid"] = float(c["r"]), uuid.UUID(c["i"])
            params["fuzzy"] = bool(c["f"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AppError("Invalid cursor", code="invalid_cursor") from exc
        cursor_sql = "WHERE (rank, id) < (:crank, :cid)"

    # Transaction-local: how forgiving the trigram match is (0.4 keeps one-letter typos).
    await db.execute(
        text("SELECT set_config('pg_trgm.word_similarity_threshold', '0.4', true)")
    )
    stmt = text(SQL.format(filters=" ".join(filters), cursor=cursor_sql))
    rows = (await db.execute(stmt, params)).all()
    if not rows and not cursor and len(q) >= 3:
        params["fuzzy"] = True
        rows = (await db.execute(stmt, params)).all()
    more = len(rows) > limit
    rows = rows[:limit]
    nxt = None
    if more:
        last = rows[-1]
        nxt = encode_cursor({"r": last.rank, "i": str(last.id), "f": params["fuzzy"]})
    return Page(
        items=[
            SearchHit(
                **{k: getattr(r, k) for k in SearchHit.model_fields if k != "snippet"},
                snippet=r.snippet,
            )
            for r in rows
        ],
        next_cursor=nxt,
    )
