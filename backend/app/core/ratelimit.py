"""Redis fixed-window rate limiting as FastAPI dependencies; 429 envelope + Retry-After.

Fails open (with a log line) if Redis is down: an outage must not lock everyone out.
"""

import logging

from fastapi import Request
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import AppError
from app.core.redis import get_redis
from app.core.security import decode_access_token

log = logging.getLogger("app.ratelimit")


def identity(request: Request, per: str) -> str:
    """Per-user key when a valid bearer token is present, otherwise the client IP."""
    if per == "user":
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            try:
                return "u:" + decode_access_token(auth[7:])["sub"]
            except AppError:
                pass
    return "ip:" + (request.client.host if request.client else "unknown")


def rate_limit(scope: str, limit: int, window: int, per: str = "ip"):
    async def dependency(request: Request) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        key = f"rl:{scope}:{identity(request, per)}"
        try:
            r = get_redis()
            count = await r.incr(key)
            if count == 1:
                await r.expire(key, window)
            ttl = await r.ttl(key)
            if ttl < 0:  # key lost its expiry (crash between incr and expire)
                await r.expire(key, window)
                ttl = window
        except RedisError:
            log.warning("rate limiter unavailable, failing open", exc_info=True)
            return
        if count > limit:
            raise AppError(
                "Too many requests. Slow down a little.",
                code="rate_limited",
                status_code=429,
                headers={"Retry-After": str(max(ttl, 1))},
            )

    return dependency


limit_auth = rate_limit(
    "auth", 20, 60
)  # per IP (campus NAT shares IPs, hence generous)
limit_write = rate_limit("write", 30, 60, per="user")
limit_vote = rate_limit("vote", 60, 60, per="user")
limit_search = rate_limit("search", 30, 60, per="user")
limit_comment = rate_limit("comment", 10, 60, per="user")
limit_upload = rate_limit("upload", 10, 60, per="user")
