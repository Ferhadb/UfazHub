from typing import Literal

from fastapi import APIRouter, Response

from app.api.deps import DB
from app.services import feeds as svc

router = APIRouter(tags=["feeds"])


async def _feed(db: DB, tag: str | None, kind: Literal["rss", "atom"]) -> Response:
    articles, title = await svc.articles_for_feed(db, tag)
    content_type = "application/rss+xml" if kind == "rss" else "application/atom+xml"
    return Response(
        svc.render_feed(articles, title, tag, kind),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/feeds/articles.rss")
async def articles_rss(db: DB) -> Response:
    return await _feed(db, None, "rss")


@router.get("/feeds/articles.atom")
async def articles_atom(db: DB) -> Response:
    return await _feed(db, None, "atom")


@router.get("/feeds/tags/{slug}.rss")
async def tag_rss(slug: str, db: DB) -> Response:
    return await _feed(db, slug, "rss")


@router.get("/feeds/tags/{slug}.atom")
async def tag_atom(slug: str, db: DB) -> Response:
    return await _feed(db, slug, "atom")
