"""arq worker: `arq app.worker.WorkerSettings`. Jobs register here as slices add them."""

import asyncio

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.mail import deliver


async def ping(ctx) -> str:
    # shortcut: placeholder so arq starts; remove once the first real job lands.
    return "pong"


async def send_email(ctx, to: str, subject: str, body: str) -> None:
    await asyncio.to_thread(deliver, to, subject, body)


class WorkerSettings:
    functions = [ping, send_email]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 120
