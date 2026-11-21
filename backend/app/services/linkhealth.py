"""Link health: an hourly arq job re-checks links; readers can report one broken.

A link is `dead` after DEAD_AFTER consecutive failed checks, or after one failure when a reader
has reported it. A passing check clears the failures and the report. Reported links go first.
"""

import asyncio
import uuid
from urllib.parse import urljoin

import httpx
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.ssrf import MAX_REDIRECTS, BlockedUrl, assert_public_url, guarded_client
from app.models.content import ContentItem, ContentStatus, ResourceLink

DEAD_AFTER = 2
BATCH = 50
CONCURRENCY = 10
RECHECK = "interval '1 day'"
DEADLINE = 10  # seconds per link, redirects included
# Bot walls and rate limits answer these for a perfectly good page: treat as alive.
UNSURE = {401, 403, 429}


async def is_alive(url: str, client: httpx.AsyncClient) -> bool:
    """HEAD, falling back to GET (some servers refuse HEAD); every redirect hop is SSRF-checked."""
    try:
        async with asyncio.timeout(DEADLINE):
            for method in ("HEAD", "GET"):
                target, status = url, 0
                for _ in range(MAX_REDIRECTS + 1):
                    await assert_public_url(target)
                    async with client.stream(method, target) as r:
                        status = r.status_code
                        if r.is_redirect:
                            target = urljoin(target, r.headers.get("location", ""))
                            continue
                    break
                else:
                    return False  # redirect loop
                if status < 400 or status in UNSURE:
                    return True
                if method == "GET" or status not in (400, 404, 405, 501):
                    return False  # HEAD said something definite (e.g. 410, 5xx)
            return False
    except (BlockedUrl, httpx.HTTPError, TimeoutError, ValueError):
        return False


async def check_links(
    db: AsyncSession, client: httpx.AsyncClient | None = None, limit: int = BATCH
) -> int:
    """Check the next `limit` links that are due; returns how many were checked."""
    due = (
        await db.execute(
            select(ResourceLink.id, ResourceLink.url)
            .join(ContentItem, ContentItem.id == ResourceLink.resource_id)
            .where(
                ContentItem.status == ContentStatus.published.value,
                ResourceLink.checked_at.is_(None)
                | (ResourceLink.checked_at < func.now() - text(RECHECK))
                | (ResourceLink.reported_broken_at > ResourceLink.checked_at),
            )
            .order_by(
                ResourceLink.reported_broken_at.is_(None),
                ResourceLink.checked_at.asc().nulls_first(),
            )
            .limit(limit)
        )
    ).all()
    owns = client is None
    client = client or guarded_client()
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(link_id, url):
        async with sem:
            return link_id, await is_alive(url, client)

    try:
        results = await asyncio.gather(*(one(i, u) for i, u in due))
    finally:
        if owns:
            await client.aclose()
    for link_id, alive in results:
        await _record(db, link_id, alive)
    await db.commit()
    return len(results)


async def _record(db: AsyncSession, link_id: uuid.UUID, alive: bool) -> None:
    if alive:
        values = dict(fail_count=0, is_dead=False, reported_broken_at=None)
    else:
        fails = ResourceLink.fail_count + 1
        values = dict(
            fail_count=fails,
            is_dead=(fails >= DEAD_AFTER)
            | ResourceLink.reported_broken_at.is_not(None),
        )
    await db.execute(
        update(ResourceLink)
        .where(ResourceLink.id == link_id)
        .values(checked_at=func.now(), **values)
    )


async def report_broken(db: AsyncSession, link_id: uuid.UUID) -> ResourceLink:
    """Flag a link of a published resource; idempotent. The next hourly run checks it first."""
    link = (
        await db.execute(
            select(ResourceLink)
            .join(ContentItem, ContentItem.id == ResourceLink.resource_id)
            .where(
                ResourceLink.id == link_id,
                ContentItem.status == ContentStatus.published.value,
            )
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if link is None:
        raise NotFound("Not found.")
    if link.reported_broken_at is None:
        link.reported_broken_at = func.now()  # type: ignore[assignment]
        await db.flush()
        await db.refresh(link)
    return link
