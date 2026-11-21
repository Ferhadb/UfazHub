import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, Conflict, Forbidden, Unauthorized
from app.core.mail import send_mail
from app.core.security import hash_password, hash_token, new_token, verify_password
from app.models.user import AuthToken, RefreshToken, User, UserStatus

VERIFY, RESET = "verify_email", "reset_password"


def _now() -> datetime:
    return datetime.now(UTC)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


def _ensure_not_banned(user: User) -> None:
    if user.status == UserStatus.banned:
        raise Forbidden("This account has been suspended.", code="account_banned")


async def signup(
    db: AsyncSession, email: str, password: str, display_name: str
) -> User:
    domains = settings.signup_domains
    if domains and email.rsplit("@", 1)[1] not in domains:
        raise AppError(
            f"Sign-up is limited to: {', '.join('@' + d for d in domains)}",
            code="signup_domain_not_allowed",
            status_code=403,
            fields={"email": "Use your university email address"},
        )
    user = User(
        email=email,
        display_name=display_name,
        password_hash=await hash_password(password),
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise Conflict(
            "That email is already registered.",
            code="email_taken",
            fields={"email": "Already registered"},
        ) from None
    await send_verification(db, user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = await get_user_by_email(db, email)
    if (
        not await verify_password(user.password_hash if user else None, password)
        or not user
    ):
        raise Unauthorized("Wrong email or password.", code="invalid_credentials")
    _ensure_not_banned(user)
    return user


# --- refresh tokens ----------------------------------------------------------
async def issue_refresh(
    db: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID | None = None
) -> str:
    raw = new_token()
    db.add(
        RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_token(raw),
            expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        )
    )
    return raw


async def revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def revoke_all(db: AsyncSession, user_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def rotate_refresh(db: AsyncSession, raw: str) -> tuple[User, str]:
    """Swap a valid refresh token for a new one in the same family.

    A token that was already rotated or revoked is being replayed (theft or a
    stale client): revoke the whole family so both parties must sign in again.
    """
    row = await db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_token(raw))
        .with_for_update()
    )
    if row is None:
        raise Unauthorized(
            "Session expired. Please sign in again.", code="invalid_refresh"
        )
    if row.used_at is not None or row.revoked_at is not None:
        await revoke_family(db, row.family_id)
        await db.commit()  # persist the revocation before failing the request
        raise Unauthorized(
            "Session expired. Please sign in again.", code="refresh_reuse"
        )
    if row.expires_at <= _now():
        raise Unauthorized(
            "Session expired. Please sign in again.", code="invalid_refresh"
        )
    user = await db.get(User, row.user_id)
    if user is None or user.status == UserStatus.banned:
        await revoke_family(db, row.family_id)
        await db.commit()
        raise Unauthorized(
            "Session expired. Please sign in again.", code="invalid_refresh"
        )
    row.used_at = _now()
    return user, await issue_refresh(db, user.id, row.family_id)


async def revoke_by_token(db: AsyncSession, raw: str) -> None:
    row = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
    )
    if row:
        await revoke_family(db, row.family_id)


# --- email verification and password reset -----------------------------------
async def _issue_auth_token(
    db: AsyncSession, user: User, kind: str, ttl: timedelta
) -> str:
    await db.execute(  # only the newest link works
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.kind == kind,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=_now())
    )
    raw = new_token()
    db.add(
        AuthToken(
            user_id=user.id,
            kind=kind,
            token_hash=hash_token(raw),
            expires_at=_now() + ttl,
        )
    )
    return raw


async def _consume(db: AsyncSession, raw: str, kind: str) -> User:
    row = await db.scalar(
        select(AuthToken)
        .where(AuthToken.token_hash == hash_token(raw), AuthToken.kind == kind)
        .with_for_update()
    )
    user = await db.get(User, row.user_id) if row else None
    if not row or not user or row.used_at is not None or row.expires_at <= _now():
        raise AppError("This link is invalid or has expired.", code="invalid_token")
    row.used_at = _now()
    return user


async def send_verification(db: AsyncSession, user: User) -> None:
    raw = await _issue_auth_token(
        db, user, VERIFY, timedelta(hours=settings.VERIFY_TOKEN_HOURS)
    )
    await send_mail(
        user.email,
        "Confirm your UFAZ Hub email",
        f"Welcome to UFAZ Hub, {user.display_name}.\n\nConfirm your email:\n"
        f"{settings.SITE_URL}/verify?token={raw}\n\nThe link works for {settings.VERIFY_TOKEN_HOURS} hours.",
    )


async def verify_email(db: AsyncSession, raw: str) -> User:
    user = await _consume(db, raw, VERIFY)
    user.email_verified_at = user.email_verified_at or _now()
    return user


async def request_reset(db: AsyncSession, email: str) -> None:
    user = await get_user_by_email(db, email)
    if user is None or user.status == UserStatus.banned:
        return  # the endpoint answers identically either way (no account enumeration)
    raw = await _issue_auth_token(
        db, user, RESET, timedelta(minutes=settings.RESET_TOKEN_MINUTES)
    )
    await send_mail(
        user.email,
        "Reset your UFAZ Hub password",
        f"Reset your password:\n{settings.SITE_URL}/reset?token={raw}\n\n"
        f"The link works for {settings.RESET_TOKEN_MINUTES} minutes. Ignore this if it wasn't you.",
    )


async def reset_password(db: AsyncSession, raw: str, password: str) -> User:
    user = await _consume(db, raw, RESET)
    user.password_hash = await hash_password(password)
    user.email_verified_at = (
        user.email_verified_at or _now()
    )  # they proved inbox control
    await revoke_all(db, user.id)
    return user
