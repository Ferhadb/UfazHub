from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.responses import Response as RawResponse

from app.api.deps import CSRF_COOKIE, REFRESH_COOKIE, DB, CurrentUser, csrf_protect
from app.core.config import settings
from app.core.errors import NotFound, Unauthorized
from app.core.ratelimit import limit_auth
from app.core.security import create_access_token, new_token
from app.models.user import User
from app.schemas.auth import (
    DevLoginIn,
    ForgotIn,
    LoginIn,
    ResetIn,
    SignupIn,
    TokenIn,
    TokenOut,
    UserOut,
)
from app.services import audit
from app.services import auth as svc

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookies(response: Response, refresh: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        path=f"{settings.API_PREFIX}/auth",
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )
    # Readable by our own JS so it can echo it in X-CSRF-Token (double submit).
    response.set_cookie(
        CSRF_COOKIE,
        new_token(),
        max_age=settings.REFRESH_TOKEN_DAYS * 86400,
        path="/",
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
    )


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=f"{settings.API_PREFIX}/auth")
    response.delete_cookie(CSRF_COOKIE, path="/")


def _token_out(user: User) -> TokenOut:
    token, ttl = create_access_token(str(user.id), user.role)
    return TokenOut(
        access_token=token, expires_in=ttl, user=UserOut.model_validate(user)
    )


@router.post(
    "/signup",
    status_code=201,
    response_model=UserOut,
    dependencies=[Depends(limit_auth)],
)
async def signup(body: SignupIn, db: DB):
    user = await svc.signup(db, body.email, body.password, body.display_name)
    await db.commit()
    return user


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limit_auth)])
async def login(body: LoginIn, response: Response, db: DB):
    user = await svc.authenticate(db, body.email, body.password)
    _set_cookies(response, await svc.issue_refresh(db, user.id))
    await db.commit()
    return _token_out(user)


@router.post("/refresh", response_model=TokenOut, dependencies=[Depends(csrf_protect)])
async def refresh(
    response: Response,
    db: DB,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
):
    if not refresh_token:
        raise Unauthorized("Not signed in.", code="no_refresh")
    user, new_refresh = await svc.rotate_refresh(db, refresh_token)
    _set_cookies(response, new_refresh)
    await db.commit()
    return _token_out(user)


@router.post("/logout", status_code=204, dependencies=[Depends(csrf_protect)])
async def logout(
    db: DB, refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None
):
    if refresh_token:
        await svc.revoke_by_token(db, refresh_token)
        await db.commit()
    response = RawResponse(status_code=204)
    _clear_cookies(response)
    return response


@router.post("/logout-all", status_code=204)
async def logout_all(db: DB, user: CurrentUser):
    await svc.revoke_all(db, user.id)
    await db.commit()
    response = RawResponse(status_code=204)
    _clear_cookies(response)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/verify-email", response_model=UserOut)
async def verify_email(body: TokenIn, db: DB):
    user = await svc.verify_email(db, body.token)
    await db.commit()
    return user


@router.post(
    "/resend-verification", status_code=202, dependencies=[Depends(limit_auth)]
)
async def resend_verification(db: DB, user: CurrentUser):
    if not user.email_verified:
        await svc.send_verification(db, user)
        await db.commit()
    return {"status": "sent"}


@router.post("/password/forgot", status_code=202, dependencies=[Depends(limit_auth)])
async def forgot_password(body: ForgotIn, db: DB):
    await svc.request_reset(db, body.email)
    await db.commit()
    return {"status": "sent"}  # identical whether or not the account exists


@router.post("/password/reset", status_code=204, dependencies=[Depends(limit_auth)])
async def reset_password(body: ResetIn, db: DB):
    user = await svc.reset_password(db, body.token, body.password)
    await audit.record(
        db,
        actor_id=user.id,
        action="auth.password_reset",
        target_type="user",
        target_id=user.id,
    )
    await db.commit()
    return RawResponse(status_code=204)


@router.post("/dev/login-as", response_model=TokenOut)
async def dev_login_as(body: DevLoginIn, response: Response, db: DB):
    """Development only: sign in as any existing user without a password."""
    if not settings.is_dev:
        raise NotFound("Not Found")
    user = await svc.get_user_by_email(db, body.email)
    if user is None:
        raise NotFound("No such user")
    await audit.record(
        db,
        actor_id=user.id,
        action="auth.dev_login_as",
        target_type="user",
        target_id=user.id,
    )
    _set_cookies(response, await svc.issue_refresh(db, user.id))
    await db.commit()
    return _token_out(user)
