"""arq worker: `arq app.worker.WorkerSettings`. Jobs register here as slices add them."""

from arq.connections import RedisSettings

from app.core.config import settings


async def ping(ctx) -> str:
    # shortcut: placeholder so arq starts; remove once the first real job lands.
    return "pong"


class WorkerSettings:
    functions = [ping]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 120
