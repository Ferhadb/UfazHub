import asyncio
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, update

from app.core.config import DEFAULT_JWT_SECRET, Settings, settings
from app.core.redis import get_redis
from app.db.session import SessionLocal
from app.models.audit import AuditLog
from app.models.user import AuthToken, RefreshToken, User
from app.schemas.common import Page, decode_cursor, encode_cursor

PW = "correct horse battery"


def new_email() -> str:
    return f"u{uuid.uuid4().hex[:10]}@example.com"


async def signup(client, email=None, password=PW):
    email = email or new_email()
    r = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": password, "display_name": "Aygün"},
    )
    return email, r


async def login(client, email, password=PW):
    return await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )


def csrf(client) -> dict:
    return {"X-CSRF-Token": client.cookies.get("csrf_token", "")}


async def registered(client):
    email, r = await signup(client)
    assert r.status_code == 201
    r = await login(client, email)
    assert r.status_code == 200
    return email, r.json()


def link_token(mail) -> str:
    return re.search(r"token=([\w-]+)", mail["body"]).group(1)


async def set_user(email, **values):
    async with SessionLocal() as db:
        await db.execute(update(User).where(User.email == email).values(**values))
        await db.commit()


# --- signup / login ------------------------------------------------------------
async def test_signup_login_me(client, outbox):
    email, r = await signup(client, email="MiXed@Example.com")
    assert r.status_code == 201
    assert r.json()["email"] == "mixed@example.com"
    assert r.json()["role"] == "user" and r.json()["email_verified"] is False
    assert "password" not in r.text
    assert len(outbox) == 1 and "/verify?token=" in outbox[0]["body"]

    r = await login(client, "mixed@example.com")
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.json()["email"] == "mixed@example.com"


async def test_refresh_cookie_flags(client):
    await registered(client)
    cookie = next(c for c in client.cookies.jar if c.name == "refresh_token")
    assert cookie.has_nonstandard_attr("HttpOnly")
    assert cookie.get_nonstandard_attr("SameSite").lower() == "lax"
    assert cookie.path == "/api/auth"


async def test_duplicate_email_and_weak_password(client):
    email, _ = await signup(client)
    _, r = await signup(client, email=email)
    assert r.status_code == 409 and r.json()["code"] == "email_taken"
    _, r = await signup(client, password="short")
    assert r.status_code == 422 and "password" in r.json()["fields"]


async def test_bad_credentials_are_uniform(client):
    email, _ = await signup(client)
    wrong = await login(client, email, "wrong password!")
    unknown = await login(client, new_email())
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["code"] == unknown.json()["code"] == "invalid_credentials"


async def test_banned_user_cannot_log_in_or_use_token(client):
    email, body = await registered(client)
    await set_user(email, status="banned")
    r = await login(client, email)
    assert r.status_code == 403 and r.json()["code"] == "account_banned"
    me = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 403
    assert (
        await client.post("/api/auth/refresh", headers=csrf(client))
    ).status_code == 401


async def test_wrong_password_for_banned_user_does_not_leak_status(client):
    email, _ = await signup(client)
    await set_user(email, status="banned")
    assert (await login(client, email, "not the password")).status_code == 401


async def test_me_requires_valid_token(client):
    assert (await client.get("/api/auth/me")).json()["code"] == "not_authenticated"
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401 and r.json()["code"] == "invalid_token"


async def test_signup_domain_restriction(client, monkeypatch):
    monkeypatch.setattr(settings, "SIGNUP_ALLOWED_DOMAINS", "ufaz.az")
    _, r = await signup(client)
    assert r.status_code == 403 and r.json()["code"] == "signup_domain_not_allowed"
    _, r = await signup(client, email=f"{uuid.uuid4().hex[:8]}@ufaz.az")
    assert r.status_code == 201


# --- refresh / CSRF -------------------------------------------------------------
async def test_refresh_rotates_token(client):
    await registered(client)
    old = client.cookies.get("refresh_token", path="/api/auth")
    r = await client.post("/api/auth/refresh", headers=csrf(client))
    assert r.status_code == 200 and r.json()["access_token"]
    assert client.cookies.get("refresh_token", path="/api/auth") != old


async def test_refresh_requires_csrf(client):
    await registered(client)
    r = await client.post("/api/auth/refresh")
    assert r.status_code == 403 and r.json()["code"] == "csrf_failed"
    r = await client.post("/api/auth/refresh", headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403
    assert (await client.post("/api/auth/logout")).status_code == 403


async def test_refresh_reuse_revokes_family(client):
    await registered(client)
    stolen = client.cookies.get("refresh_token", path="/api/auth")
    assert (
        await client.post("/api/auth/refresh", headers=csrf(client))
    ).status_code == 200
    legit = client.cookies.get("refresh_token", path="/api/auth")

    # An attacker replays the already-rotated token.
    client.cookies.set("refresh_token", stolen, path="/api/auth", domain="test.local")
    r = await client.post("/api/auth/refresh", headers=csrf(client))
    assert r.status_code == 401 and r.json()["code"] == "refresh_reuse"

    # The legitimate (newest) token is dead too: the whole family was revoked.
    client.cookies.set("refresh_token", legit, path="/api/auth", domain="test.local")
    r = await client.post("/api/auth/refresh", headers=csrf(client))
    assert r.status_code == 401


async def test_expired_refresh_rejected(client):
    await registered(client)
    async with SessionLocal() as db:
        await db.execute(
            update(RefreshToken).values(expires_at=datetime.now(UTC) - timedelta(1))
        )
        await db.commit()
    assert (
        await client.post("/api/auth/refresh", headers=csrf(client))
    ).status_code == 401


async def test_refresh_without_cookie(client):
    client.cookies.set("csrf_token", "x", path="/", domain="test.local")
    r = await client.post("/api/auth/refresh", headers={"X-CSRF-Token": "x"})
    assert r.status_code == 401 and r.json()["code"] == "no_refresh"


def replay(client, token):
    """Put a captured refresh token (plus a matching CSRF pair) back on the client."""
    client.cookies.set("refresh_token", token, path="/api/auth", domain="test.local")
    client.cookies.set("csrf_token", "c", path="/", domain="test.local")
    return {"X-CSRF-Token": "c"}


async def test_logout_revokes_session(client):
    await registered(client)
    token = client.cookies.get("refresh_token", path="/api/auth")
    assert (
        await client.post("/api/auth/logout", headers=csrf(client))
    ).status_code == 204
    assert not client.cookies.get("refresh_token", path="/api/auth")  # cookie cleared
    r = await client.post("/api/auth/refresh", headers=replay(client, token))
    assert r.status_code == 401


async def test_logout_requires_csrf(client):
    await registered(client)
    r = await client.post("/api/auth/logout")
    assert r.status_code == 403 and r.json()["code"] == "csrf_failed"
    r = await client.post("/api/auth/logout", headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403
    assert client.cookies.get("refresh_token", path="/api/auth")  # session untouched


async def test_logout_everywhere(client):
    email, body = await registered(client)
    first = client.cookies.get("refresh_token", path="/api/auth")
    other = await login(client, email)  # second device
    second = client.cookies.get("refresh_token", path="/api/auth")
    assert other.status_code == 200
    r = await client.post(
        "/api/auth/logout-all",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert r.status_code == 204
    for token in (first, second):
        assert (
            await client.post("/api/auth/refresh", headers=replay(client, token))
        ).status_code == 401


# --- email verification ----------------------------------------------------------
async def test_verify_email_flow(client, outbox):
    email, body = await registered(client)
    token = link_token(outbox[0])
    r = await client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 200 and r.json()["email_verified"] is True
    again = await client.post("/api/auth/verify-email", json={"token": token})
    assert again.status_code == 400 and again.json()["code"] == "invalid_token"
    assert (
        await client.post("/api/auth/verify-email", json={"token": "x" * 30})
    ).status_code == 400


async def test_resend_verification_invalidates_old_link(client, outbox):
    _, body = await registered(client)
    r = await client.post(
        "/api/auth/resend-verification",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert r.status_code == 202 and len(outbox) == 2
    old = await client.post(
        "/api/auth/verify-email", json={"token": link_token(outbox[0])}
    )
    assert old.status_code == 400
    assert (
        await client.post(
            "/api/auth/verify-email", json={"token": link_token(outbox[1])}
        )
    ).status_code == 200


async def test_verify_token_expiry_and_hashed_storage(client, outbox):
    await registered(client)
    token = link_token(outbox[0])
    async with SessionLocal() as db:
        stored = (await db.scalars(select(AuthToken.token_hash))).all()
        assert token not in stored  # only the hash is stored
        await db.execute(
            update(AuthToken).values(expires_at=datetime.now(UTC) - timedelta(1))
        )
        await db.commit()
    assert (
        await client.post("/api/auth/verify-email", json={"token": token})
    ).status_code == 400


# --- password reset --------------------------------------------------------------
async def test_password_reset_flow(client, outbox):
    email, body = await registered(client)
    r = await client.post("/api/auth/password/forgot", json={"email": email})
    assert r.status_code == 202
    token = link_token(outbox[-1])
    assert "/reset?token=" in outbox[-1]["body"]

    new_pw = "a brand new passphrase"
    r = await client.post(
        "/api/auth/password/reset", json={"token": token, "password": new_pw}
    )
    assert r.status_code == 204
    assert (await login(client, email)).status_code == 401  # old password dead
    assert (await login(client, email, new_pw)).status_code == 200
    reuse = await client.post(
        "/api/auth/password/reset", json={"token": token, "password": new_pw}
    )
    assert reuse.status_code == 400

    async with SessionLocal() as db:
        row = await db.scalar(
            select(AuditLog).where(AuditLog.action == "auth.password_reset")
        )
        assert row and row.target_type == "user"


async def test_password_reset_revokes_sessions(client, outbox):
    email, _ = await registered(client)
    refresh = client.cookies.get("refresh_token", path="/api/auth")
    await client.post("/api/auth/password/forgot", json={"email": email})
    await client.post(
        "/api/auth/password/reset",
        json={"token": link_token(outbox[-1]), "password": "another long passphrase"},
    )
    client.cookies.set("refresh_token", refresh, path="/api/auth", domain="test.local")
    assert (
        await client.post("/api/auth/refresh", headers=csrf(client))
    ).status_code == 401


async def test_forgot_does_not_reveal_accounts(client, outbox):
    r = await client.post("/api/auth/password/forgot", json={"email": new_email()})
    assert r.status_code == 202 and r.json() == {"status": "sent"} and outbox == []


# --- dev login-as ------------------------------------------------------------------
async def test_dev_login_as_only_in_development(client, monkeypatch):
    email, _ = await signup(client)
    r = await client.post("/api/auth/dev/login-as", json={"email": email})
    assert r.status_code == 404  # APP_ENV=test
    monkeypatch.setattr(settings, "APP_ENV", "development")
    r = await client.post("/api/auth/dev/login-as", json={"email": email})
    assert r.status_code == 200 and r.json()["user"]["email"] == email
    r = await client.post("/api/auth/dev/login-as", json={"email": new_email()})
    assert r.status_code == 404


# --- rate limiting -----------------------------------------------------------------
async def test_login_rate_limited_with_retry_after(client):
    try:
        await get_redis().ping()
    except Exception:
        pytest.skip("redis not running")
    email = new_email()
    for _ in range(20):
        assert (await login(client, email)).status_code == 401
    r = await login(client, email)
    assert r.status_code == 429
    assert r.json()["code"] == "rate_limited" and r.json()["request_id"]
    assert 1 <= int(r.headers["retry-after"]) <= 60


async def test_rate_limit_window_resets():
    from starlette.requests import Request

    from app.core.errors import AppError
    from app.core.ratelimit import rate_limit

    try:
        await get_redis().ping()
    except Exception:
        pytest.skip("redis not running")
    dep = rate_limit("t-reset", 2, 1)
    req = Request({"type": "http", "headers": [], "client": ("7.7.7.7", 1)})
    await dep(req)
    await dep(req)
    with pytest.raises(AppError) as e:
        await dep(req)
    assert e.value.status_code == 429
    await asyncio.sleep(1.2)
    await dep(req)  # new window


async def test_rate_limit_fails_open_when_redis_down(monkeypatch):
    from redis.asyncio import Redis
    from starlette.requests import Request

    import app.core.ratelimit as rl

    dead = Redis.from_url("redis://127.0.0.1:1/0", socket_connect_timeout=0.2)
    monkeypatch.setattr(rl, "get_redis", lambda: dead)
    req = Request({"type": "http", "headers": [], "client": ("8.8.8.8", 1)})
    await rl.rate_limit("t-open", 1, 60)(req)  # must not raise
    await rl.rate_limit("t-open", 1, 60)(req)


async def test_rate_limit_identity_is_per_user_with_token():
    from starlette.requests import Request

    from app.core.ratelimit import identity
    from app.core.security import create_access_token

    token, _ = create_access_token("user-1", "user")

    def req(auth=""):
        h = [(b"authorization", auth.encode())] if auth else []
        return Request({"type": "http", "headers": h, "client": ("9.9.9.9", 1)})

    assert identity(req(f"Bearer {token}"), "user") == "u:user-1"
    assert identity(req("Bearer junk"), "user") == "ip:9.9.9.9"
    assert identity(req(f"Bearer {token}"), "ip") == "ip:9.9.9.9"


# --- config, pagination, audit -------------------------------------------------------
def test_production_refuses_default_secret_and_insecure_cookie():
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(
            APP_ENV="production", COOKIE_SECURE=True, JWT_SECRET_KEY=DEFAULT_JWT_SECRET
        )
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="x" * 40)
    with pytest.raises(ValueError, match="SITE_URL"):
        Settings(APP_ENV="production", JWT_SECRET_KEY="x" * 40, COOKIE_SECURE=True)


@pytest.mark.parametrize(
    "origin",
    ["http://ufazhub.xyz", "https://localhost", "*", "https://ufazhub.xyz/path"],
)
def test_production_rejects_unsafe_cors_origins(origin):
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="x" * 40,
            COOKIE_SECURE=True,
            SITE_URL="https://ufazhub.xyz",
            CORS_ORIGINS=[origin],
        )


def test_production_accepts_https_cors_allowlist():
    config = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="x" * 40,
        COOKIE_SECURE=True,
        SITE_URL="https://ufazhub.xyz",
        CORS_ORIGINS=["https://ufazhub.xyz"],
    )
    assert config.CORS_ORIGINS == ["https://ufazhub.xyz"]


def test_page_cursor_roundtrip():
    cursor = encode_cursor({"id": "abc", "n": 3})
    assert decode_cursor(cursor) == {"id": "abc", "n": 3}
    assert Page[int](items=[1, 2], next_cursor=cursor).model_dump()["items"] == [1, 2]
    from app.core.errors import AppError

    for bad in ("!!!", "e30xx", "WzFd"):  # not base64, not JSON, JSON but not an object
        with pytest.raises(AppError):
            decode_cursor(bad)


async def test_audit_record_stores_only_changed_keys():
    from app.services import audit

    async with SessionLocal() as db:
        row = await audit.record(
            db,
            actor_id=None,
            action="user.role_change",
            target_type="user",
            target_id="abc",
            before={"role": "user", "status": "active"},
            after={"role": "admin", "status": "active"},
            reason="promoted",
        )
        await db.commit()
        assert row.before == {"role": "user"} and row.after == {"role": "admin"}
