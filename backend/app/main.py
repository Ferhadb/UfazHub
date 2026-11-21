from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin,
    articles,
    auth,
    collections,
    comments,
    content,
    health,
    moderation,
    notifications,
    questions,
    uploads,
)
from app.core.config import settings
from app.core.errors import ErrorBody, install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.core.redis import get_redis
from app.db.session import engine

configure_logging(settings.LOG_LEVEL)

if settings.SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.APP_ENV)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    # Graceful shutdown: uvicorn drains requests, then we close pools.
    await get_redis().aclose()
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_PREFIX}/openapi.json",
    docs_url=f"{settings.API_PREFIX}/docs",
    redoc_url=None,
    lifespan=lifespan,
    responses={"default": {"model": ErrorBody, "description": "Error envelope"}},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)
app.add_middleware(RequestIdMiddleware)
install_error_handlers(app)

app.include_router(health.router, prefix=settings.API_PREFIX)
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(content.router, prefix=settings.API_PREFIX)
app.include_router(articles.router, prefix=settings.API_PREFIX)
app.include_router(collections.router, prefix=settings.API_PREFIX)
app.include_router(comments.router, prefix=settings.API_PREFIX)
app.include_router(uploads.router, prefix=settings.API_PREFIX)
app.include_router(questions.router, prefix=settings.API_PREFIX)
app.include_router(notifications.router, prefix=settings.API_PREFIX)
app.include_router(moderation.router, prefix=settings.API_PREFIX)
app.include_router(admin.router, prefix=settings.API_PREFIX)
