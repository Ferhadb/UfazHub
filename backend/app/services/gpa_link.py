"""Sign in with UFAZ GPA: GPA vouches for a student, Hub links or creates the account."""

from datetime import UTC, datetime
from urllib.parse import quote

import httpx
import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, Conflict, Unauthorized
from app.core.redis import get_redis
from app.models.user import RefreshToken, Role, User
from app.services.auth import _ensure_not_banned


def _bad(msg: str = "That GPA sign-in link is invalid or has expired.") -> Unauthorized:
    return Unauthorized(msg, code="gpa_invalid_token")


async def _claims(token: str, state: str) -> dict:
    if not settings.GPA_SSO_SECRET:
        raise AppError(
            "Sign in with UFAZ GPA is not enabled.",
            code="gpa_disabled",
            status_code=503,
        )
    try:
        c = jwt.decode(
            token,
            settings.GPA_SSO_SECRET,
            algorithms=["HS256"],
            audience="ufazhub",
            issuer="ufazgpa",
            options={"require": ["exp", "sub", "jti", "nonce"]},
        )
    except jwt.PyJWTError:
        raise _bad() from None
    if c["nonce"] != state:
        raise _bad()
    try:  # single use; if Redis is down the 60 s lifetime and nonce still bind it
        if not await get_redis().set(f"gpa:jti:{c['jti']}", 1, nx=True, ex=120):
            raise _bad()
    except AppError:
        raise
    except Exception:
        pass
    return c


async def sign_in(db: AsyncSession, token: str, state: str) -> User:
    c = await _claims(token, state)
    gpa_id = str(c["sub"]).strip()[:32]
    name = (c.get("name") or gpa_id).strip()[:80] or gpa_id
    email = (c.get("email") or "").strip().lower() or None

    user = await db.scalar(select(User).where(User.gpa_id == gpa_id))
    if user is None:
        if not email:
            raise AppError(
                "Your UFAZ GPA account has no UFAZ email yet. Add it on UFAZ GPA and try again.",
                code="gpa_no_email",
                status_code=422,
            )
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, display_name=name, gpa_id=gpa_id)
            db.add(user)
        elif user.gpa_id:
            raise Conflict(
                "That email belongs to another linked account.", code="gpa_conflict"
            )
        else:
            user.gpa_id = gpa_id
            if user.email_verified_at is None:
                # Someone registered this address here before the owner proved it: drop their
                # password and sessions so only the GPA-verified owner gets in.
                user.password_hash = None
                await db.execute(
                    update(RefreshToken)
                    .where(
                        RefreshToken.user_id == user.id,
                        RefreshToken.revoked_at.is_(None),
                    )
                    .values(revoked_at=datetime.now(UTC))
                )
    await pull_profile(user)
    await db.flush()  # applies server defaults (role) to a new row
    _ensure_not_banned(user)
    user.email_verified_at = user.email_verified_at or datetime.now(UTC)
    if user.role == Role.user:  # GPA accounts come from the official student lists
        user.role = Role.verified_ufazian
    return user


async def pull_profile(user: User) -> None:
    """Copy the student's GPA look and links onto the Hub user. Best effort: never blocks sign-in."""
    if not (settings.GPA_SSO_SECRET and user.gpa_id):
        return
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            r = await client.get(
                f"{settings.GPA_URL.rstrip('/')}/api/sso/hub/profile/{quote(user.gpa_id)}",
                headers={"X-Hub-Secret": settings.GPA_SSO_SECRET},
            )
        if r.status_code == 200:
            user.gpa_profile = r.json()
    except (httpx.HTTPError, ValueError):
        pass
