import time
import uuid

import jwt
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User

from .test_auth import PW, login, new_email, signup

SECRET = "x" * 40
STATE = "s" * 24


@pytest.fixture(autouse=True)
def _secret(monkeypatch):
    monkeypatch.setattr(settings, "GPA_SSO_SECRET", SECRET)


def token(sub="gpa123", email=None, **over):
    claims = {
        "iss": "ufazgpa",
        "aud": "ufazhub",
        "sub": sub,
        "name": "Leyla Aliyeva",
        "email": email,
        "nonce": STATE,
        "jti": uuid.uuid4().hex,
        "exp": int(time.time()) + 60,
    } | over
    return jwt.encode(claims, SECRET, algorithm="HS256")


async def go(client, tok, state=STATE):
    return await client.post("/api/auth/gpa", json={"token": tok, "state": state})


async def test_new_student_is_created_verified(client):
    email = new_email()
    r = await go(client, token(sub=f"g{uuid.uuid4().hex[:8]}", email=email))
    assert r.status_code == 200, r.text
    u = r.json()["user"]
    assert u["role"] == "verified_ufazian" and u["email_verified"]
    assert u["email"] == email


async def test_returning_student_reuses_account(client):
    sub = f"g{uuid.uuid4().hex[:8]}"
    email = new_email()
    a = (await go(client, token(sub=sub, email=email))).json()["user"]["id"]
    b = (await go(client, token(sub=sub, email=None))).json()["user"]["id"]
    assert a == b


async def test_replay_wrong_state_bad_signature_and_expiry_are_refused(client):
    tok = token(sub=f"g{uuid.uuid4().hex[:8]}", email=new_email())
    assert (await go(client, tok)).status_code == 200
    assert (await go(client, tok)).status_code == 401  # single use
    fresh = token(sub="gx", email=new_email())
    assert (await go(client, fresh, state="o" * 24)).status_code == 401
    forged = jwt.encode({"sub": "gx"}, "y" * 40, algorithm="HS256")
    assert (await go(client, forged)).status_code == 401
    assert (await go(client, token(exp=int(time.time()) - 5))).status_code == 401


async def test_needs_email_for_first_sign_in(client):
    r = await go(client, token(sub=f"g{uuid.uuid4().hex[:8]}", email=None))
    assert r.json()["code"] == "gpa_no_email"


async def test_links_and_verifies_existing_hub_account_and_drops_squatter_password(
    client,
):
    email, _ = await signup(client)  # unverified signup with the victim's address
    sub = f"g{uuid.uuid4().hex[:8]}"
    r = await go(client, token(sub=sub, email=email))
    assert r.json()["user"]["role"] == "verified_ufazian"
    assert (await login(client, email, PW)).status_code == 401
    async with SessionLocal() as db:
        assert (await db.scalar(select(User).where(User.email == email))).gpa_id == sub


async def test_disabled_without_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "GPA_SSO_SECRET", "")
    assert (await go(client, token(email=new_email()))).status_code == 503


async def test_person_by_gpa_and_profile_link(client):
    sub = f"g{uuid.uuid4().hex[:8]}"
    uid = (await go(client, token(sub=sub, email=new_email()))).json()["user"]["id"]
    r = await client.get(f"/api/people/by-gpa/{sub}")
    assert r.json() == {"id": uid}
    assert (await client.get("/api/people/by-gpa/nobody")).status_code == 404
    p = (await client.get(f"/api/people/{uid}")).json()
    assert p["gpa_url"].endswith(f"/u/{sub}")


async def test_profile_look_is_copied_from_gpa(client, monkeypatch):
    class R:
        status_code = 200

        def json(self):
            return {
                "bio": "Skill issue",
                "supporter_tier": 2,
                "equipped": {
                    "avatar": "abc123",
                    "banner": "banner-c-red",
                    "frame": "frame-ring",
                },
                "socials": [
                    {
                        "platform": "github",
                        "handle": "me",
                        "url": "https://github.com/me",
                    }
                ],
            }

    class C:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, headers):
            assert headers["X-Hub-Secret"] == SECRET
            return R()

    monkeypatch.setattr("app.services.gpa_link.httpx.AsyncClient", lambda **k: C())
    sub = f"g{uuid.uuid4().hex[:8]}"
    r = await go(client, token(sub=sub, email=new_email()))
    u = r.json()["user"]
    assert u["avatar_url"].endswith("/api/avatars/abc123")
    p = (await client.get(f"/api/people/{u['id']}")).json()
    assert p["bio"] == "Skill issue" and p["supporter_tier"] == 2
    assert p["cosmetics"] == {"banner": "banner-c-red", "frame": "frame-ring"}
    assert p["socials"]["github"] == "https://github.com/me"
