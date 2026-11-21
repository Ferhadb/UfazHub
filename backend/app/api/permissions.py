"""Permission layer for write endpoints. Later slices reuse these dependencies as-is.

guest            -> 401 on every write
banned           -> 403 (rejected in `current_user`, even with a still-valid token)
muted            -> 403 on every write (`ActiveUser`)
unverified email -> 403 on content creation (`VerifiedUser`)
admin            -> `AdminUser`, plus `can_manage` on anyone's content
"""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import DB, CurrentUser, _bearer, current_user
from app.core.errors import Forbidden, NotFound
from app.models.content import ContentItem, ContentStatus
from app.models.user import Role, User, UserStatus


async def optional_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User | None:
    """The signed-in user, or None for guests. A bad or expired token still fails loudly."""
    return await current_user(db, creds) if creds else None


def active_user(user: CurrentUser) -> User:
    if user.status == UserStatus.muted:
        raise Forbidden("Your account is muted.", code="account_muted")
    return user


ActiveUser = Annotated[User, Depends(active_user)]


def verified_user(user: ActiveUser) -> User:
    if not user.email_verified:
        raise Forbidden("Verify your email first.", code="email_not_verified")
    return user


VerifiedUser = Annotated[User, Depends(verified_user)]


def admin_user(user: ActiveUser) -> User:
    if user.role != Role.admin:
        raise Forbidden("Admins only.")
    return user


AdminUser = Annotated[User, Depends(admin_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]


def can_manage(user: User, item: ContentItem) -> bool:
    return user.role == Role.admin or item.author_id == user.id


def initial_status(user: User) -> str:
    """Verified students and admins publish directly; everyone else waits for review."""
    trusted = user.role in (Role.verified_ufazian, Role.admin)
    return (ContentStatus.published if trusted else ContentStatus.pending_review).value


def can_view(user: User | None, item: ContentItem) -> bool:
    if item.status == ContentStatus.published:
        return True
    return user is not None and can_manage(user, item)


def not_found_unless_visible(
    user: User | None, item: ContentItem | None
) -> ContentItem:
    if item is None or not can_view(user, item):
        raise NotFound("Not found.")
    return item
