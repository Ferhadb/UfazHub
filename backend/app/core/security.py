"""Password hashing (argon2id), opaque-token hashing, short-lived access JWTs."""

import asyncio
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings
from app.core.errors import Unauthorized

_ph = PasswordHasher()
_DUMMY_HASH = _ph.hash("not-a-real-password")  # equalises timing for unknown emails


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_ph.hash, password)


async def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return await asyncio.to_thread(
            _ph.verify, password_hash or _DUMMY_HASH, password
        ) and bool(password_hash)
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    ttl = timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    now = datetime.now(UTC)
    claims = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "typ": "access",
    }
    return jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm="HS256"), int(
        ttl.total_seconds()
    )


def decode_access_token(token: str) -> dict:
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise Unauthorized("Invalid or expired token", code="invalid_token") from exc
    if claims.get("typ") != "access":
        raise Unauthorized("Invalid or expired token", code="invalid_token")
    return claims
