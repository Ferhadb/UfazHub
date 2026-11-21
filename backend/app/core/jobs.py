"""Enqueue arq jobs. Failures are logged, never raised: a job outage must not fail a request."""

import logging

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings

log = logging.getLogger("app.jobs")
enqueued: list[tuple] = []  # APP_ENV=test captures jobs here instead of enqueuing


async def enqueue(name: str, *args) -> None:
    if settings.APP_ENV == "test":
        enqueued.append((name, *args))
        return
    try:
        pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        await pool.enqueue_job(name, *args)
        await pool.aclose()
    except Exception:
        log.exception("could not enqueue %s", name)
