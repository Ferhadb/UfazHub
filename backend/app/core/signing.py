"""HMAC-signed, expiring media URLs: `/api/media/{attachment_id}/{variant}?exp=...&sig=...`."""

import hashlib
import hmac
import time
import uuid

from app.core.config import settings


def _sig(attachment_id: uuid.UUID, variant: str, exp: int) -> str:
    msg = f"{attachment_id}:{variant}:{exp}".encode()
    return hmac.new(settings.media_key, msg, hashlib.sha256).hexdigest()


def sign_media(attachment_id: uuid.UUID, variant: str, now: float | None = None) -> str:
    ttl = settings.MEDIA_URL_TTL_SECONDS
    # Expiry snaps to a ttl boundary so a URL is stable within a window (cacheable) and
    # lives between one and two ttls.
    exp = (int(now or time.time()) // ttl + 2) * ttl
    prefix = f"{settings.API_PREFIX}/media/{attachment_id}/{variant}"
    return f"{prefix}?exp={exp}&sig={_sig(attachment_id, variant, exp)}"


def verify_media(
    attachment_id: uuid.UUID, variant: str, exp: int, sig: str, now: float | None = None
) -> bool:
    if exp < (now or time.time()):
        return False
    return hmac.compare_digest(_sig(attachment_id, variant, exp), sig)
