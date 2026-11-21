"""Link previews: title, favicon and OG image for a resource link, fetched by an arq job."""

import asyncio
import uuid
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ssrf import (
    MAX_REDIRECTS,
    BlockedUrl,
    assert_public_url,
    guarded_client,
)
from app.models.content import ResourceLink

MAX_BYTES = 512 * 1024
DEADLINE = 10  # seconds for the whole fetch, redirects included


class _Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.og: dict[str, str] = {}
        self.icon: str | None = None
        self._in_title = False
        self.done = False

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and a.get("property", "").startswith("og:"):
            self.og.setdefault(a["property"], a.get("content", ""))
        elif tag == "link" and "icon" in a.get("rel", "").lower().split():
            self.icon = self.icon or a.get("href")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "head":
            self.done = True

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def parse_preview(html: str, base_url: str) -> dict[str, str | None]:
    p = _Head()
    p.feed(html)

    def absolute(u: str | None) -> str | None:
        if not u:
            return None
        full = urljoin(base_url, u.strip())
        return full[:2048] if full.startswith(("http://", "https://")) else None

    title = (p.og.get("og:title") or p.title).strip()
    return {
        "title": " ".join(title.split())[:200] or None,
        "image": absolute(p.og.get("og:image")),
        "favicon": absolute(p.icon),
    }


async def fetch_html(url: str, client: httpx.AsyncClient) -> tuple[str, str]:
    """GET with manual redirects: every hop is re-validated. Returns (final_url, html)."""
    for _ in range(MAX_REDIRECTS + 1):
        await assert_public_url(url)
        async with client.stream("GET", url, headers={"Accept": "text/html"}) as r:
            if r.is_redirect:
                url = urljoin(url, r.headers.get("location", ""))
                continue
            r.raise_for_status()
            if "html" not in r.headers.get("content-type", ""):
                raise BlockedUrl("not an HTML page")
            body = b""
            async for chunk in r.aiter_bytes():
                body += chunk
                if len(body) >= MAX_BYTES:
                    break
            return url, body[:MAX_BYTES].decode(r.encoding or "utf-8", "replace")
    raise BlockedUrl("too many redirects")


async def refresh_link_preview(
    db: AsyncSession, link_id: uuid.UUID, client: httpx.AsyncClient | None = None
) -> bool:
    """Fetch and store the preview. A failed fetch still stamps `preview_fetched_at` (no retry storm)."""
    link = await db.get(ResourceLink, link_id)
    if link is None:
        return False
    owns = client is None
    client = client or guarded_client()
    data: dict[str, str | None] = {}
    try:
        async with asyncio.timeout(DEADLINE):
            final, html = await fetch_html(link.url, client)
        data = parse_preview(html, final)
    except (BlockedUrl, httpx.HTTPError, TimeoutError, ValueError):
        data = {}
    finally:
        if owns:
            await client.aclose()
    link.preview_title = data.get("title")
    link.preview_image = data.get("image")
    link.preview_favicon = data.get("favicon")
    link.preview_fetched_at = func.now()  # type: ignore[assignment]
    await db.commit()
    return bool(data.get("title"))
