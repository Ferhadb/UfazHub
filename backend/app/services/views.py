"""Count at most one view per item and visitor in a rolling 24-hour window.

The browser holds a random cookie. The database only sees an item-specific HMAC,
which cannot be used to follow a visitor across items. No IP or user ID is stored.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFound
from app.models.content import ContentItem, ContentStatus, ContentView
from app.models.user import AuthToken, RefreshToken

VISITOR_COOKIE = "ufaz_visitor"
COOKIE_AGE = 30 * 24 * 3600
VIEW_WINDOW = timedelta(hours=24)
RETENTION_GRACE = timedelta(days=30)


def visitor_token(raw: str | None) -> tuple[str, bool]:
    """Never trust a supplied cookie as a key; invalid values receive a fresh token."""
    if raw and len(raw) == 64 and all(c in "0123456789abcdef" for c in raw):
        return raw, False
    return secrets.token_hex(32), True


async def record_view(db: AsyncSession, item_id: uuid.UUID, token: str) -> int:
    exists = await db.scalar(
        select(ContentItem.id).where(
            ContentItem.id == item_id,
            ContentItem.status == ContentStatus.published.value,
        )
    )
    if exists is None:
        raise NotFound("Not found.")

    now = datetime.now(UTC)
    digest = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        f"view:{item_id}:{token}".encode(),
        hashlib.sha256,
    ).hexdigest()
    receipt = (
        insert(ContentView)
        .values(item_id=item_id, visitor_hash=digest, viewed_at=now)
        .on_conflict_do_update(
            index_elements=[ContentView.item_id, ContentView.visitor_hash],
            set_={"viewed_at": now},
            where=ContentView.viewed_at <= now - VIEW_WINDOW,
        )
        .returning(ContentView.item_id)
    )
    counted = (await db.scalar(receipt)) is not None
    if counted:
        count = await db.scalar(
            update(ContentItem)
            .where(
                ContentItem.id == item_id,
                ContentItem.status == ContentStatus.published.value,
            )
            .values(view_count=ContentItem.view_count + 1)
            .returning(ContentItem.view_count)
        )
        if count is None:
            raise NotFound("Not found.")
    else:
        count = await db.scalar(
            select(ContentItem.view_count).where(ContentItem.id == item_id)
        )
    await db.commit()
    return count


async def cleanup_retention(db: AsyncSession, now: datetime | None = None) -> int:
    """Remove expired view receipts and old tokens without touching aggregate counts."""
    now = now or datetime.now(UTC)
    statements = (
        delete(ContentView).where(ContentView.viewed_at <= now - VIEW_WINDOW),
        delete(AuthToken).where(AuthToken.expires_at <= now - RETENTION_GRACE),
        delete(RefreshToken).where(RefreshToken.expires_at <= now - RETENTION_GRACE),
    )
    removed = 0
    for statement in statements:
        result = await db.execute(statement)
        removed += result.rowcount
    await db.commit()
    return removed
