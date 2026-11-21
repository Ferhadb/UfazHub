"""arq worker: `arq app.worker.WorkerSettings`. Jobs register here as slices add them."""

import asyncio
import uuid

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.mail import deliver
from app.db.session import SessionLocal
from app.services.previews import refresh_link_preview


async def ping(ctx) -> str:
    # shortcut: placeholder so arq starts; remove once the first real job lands.
    return "pong"


async def send_email(ctx, to: str, subject: str, body: str) -> None:
    await asyncio.to_thread(deliver, to, subject, body)


async def fetch_link_preview(ctx, link_id: str) -> bool:
    async with SessionLocal() as db:
        return await refresh_link_preview(db, uuid.UUID(link_id))


class WorkerSettings:
    functions = [ping, send_email, fetch_link_preview]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 120
