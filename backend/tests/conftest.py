"""Tests run against a real Postgres (TEST_DATABASE_URL), never SQLite.

Local: `make test-db` starts one on :5433. CI: a postgres:16 service container.
"""

import os
import subprocess
import sys

TEST_DB = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres@localhost:5433/ufazhub_test"
)
os.environ["DATABASE_URL"] = TEST_DB
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-" + "x" * 40)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402


def alembic(*args: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=True,
        env={**os.environ, "DATABASE_URL": TEST_DB},
        capture_output=True,
    )


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    alembic("downgrade", "base")
    alembic("upgrade", "head")
    yield


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture(autouse=True)
async def clean_redis():
    """Each test starts with empty rate-limit counters (redis db 15). No Redis: limiter fails open."""
    from app.core.redis import get_redis

    try:
        await get_redis().flushdb()
    except Exception:
        pass


@pytest.fixture
def outbox():
    from app.core import mail

    mail.outbox.clear()
    return mail.outbox
