from typing import Annotated
import hmac
import uuid

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import Role, User, UserStatus

DB = Annotated[AsyncSession, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)

REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "x-csrf-token"


async def current_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    if creds is None:
        raise Unauthorized("Sign in to continue.", code="not_authenticated")
    claims = decode_access_token(creds.credentials)
    user = await db.get(User, uuid.UUID(claims["sub"]))
    if user is None:
        raise Unauthorized("Sign in to continue.", code="not_authenticated")
    if user.status == UserStatus.banned:
        raise Forbidden("This account has been suspended.", code="account_banned")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def require_admin(user: CurrentUser) -> User:
    if user.role != Role.admin:
        raise Forbidden("Admins only.")
    return user


def csrf_protect(request: Request) -> None:
    """Double-submit check for cookie-authenticated endpoints (refresh, logout)."""
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get(CSRF_HEADER, "")
    if not cookie or not hmac.compare_digest(cookie.encode(), header.encode()):
        raise AppError(
            "Missing or invalid CSRF token.", code="csrf_failed", status_code=403
        )
