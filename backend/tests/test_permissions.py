"""Permission matrix: every actor x every write endpoint."""

import uuid

import pytest

from tests.factories import make_resource, make_user, resource_payload

ACTORS = {
    "guest": None,
    "unverified": dict(role="user", verified=False),
    "user": dict(role="user"),
    "verified": dict(role="verified_ufazian"),
    "admin": dict(role="admin"),
    "muted": dict(role="verified_ufazian", status="muted"),
    "banned": dict(role="verified_ufazian", status="banned"),
}

# endpoint -> expected status per actor
MATRIX = {
    "create": dict(
        guest=401,
        unverified=403,
        user=201,
        verified=201,
        admin=201,
        muted=403,
        banned=403,
    ),
    "edit_others": dict(
        guest=401,
        unverified=403,
        user=403,
        verified=403,
        admin=200,
        muted=403,
        banned=403,
    ),
    "vote": dict(
        guest=401,
        unverified=200,
        user=200,
        verified=200,
        admin=200,
        muted=403,
        banned=403,
    ),
    "bookmark": dict(
        guest=401,
        unverified=200,
        user=200,
        verified=200,
        admin=200,
        muted=403,
        banned=403,
    ),
    "unbookmark": dict(
        guest=401,
        unverified=200,
        user=200,
        verified=200,
        admin=200,
        muted=403,
        banned=403,
    ),
    "hide": dict(
        guest=401,
        unverified=403,
        user=403,
        verified=403,
        admin=204,
        muted=403,
        banned=403,
    ),
    "publish": dict(
        guest=401,
        unverified=403,
        user=403,
        verified=403,
        admin=204,
        muted=403,
        banned=403,
    ),
}

CASES = [(e, a, s) for e, row in MATRIX.items() for a, s in row.items()]


@pytest.mark.parametrize("endpoint,actor,expected", CASES)
async def test_permission_matrix(client, endpoint, actor, expected):
    _, owner = await make_user(role="verified_ufazian")
    item = await make_resource(client, owner)
    headers = {}
    if ACTORS[actor] is not None:
        _, headers = await make_user(**ACTORS[actor])
    base = f"/api/content/{item['id']}"
    call = {
        "create": lambda: client.post(
            "/api/resources", json=resource_payload(), headers=headers
        ),
        "edit_others": lambda: client.patch(
            f"/api/resources/{item['id']}",
            json={"title": "Edited by someone"},
            headers=headers,
        ),
        "vote": lambda: client.put(f"{base}/vote", json={"value": 1}, headers=headers),
        "bookmark": lambda: client.put(f"{base}/bookmark", headers=headers),
        "unbookmark": lambda: client.delete(f"{base}/bookmark", headers=headers),
        "hide": lambda: client.post(
            f"{base}/hide", json={"reason": "spam link"}, headers=headers
        ),
        "publish": lambda: client.post(f"{base}/publish", headers=headers),
    }[endpoint]
    r = await call()
    assert r.status_code == expected, r.text


async def test_error_codes_are_specific(client):
    _, h = await make_user(status="muted")
    r = await client.post("/api/resources", json=resource_payload(), headers=h)
    assert r.json()["code"] == "account_muted"
    _, h = await make_user(verified=False)
    r = await client.post("/api/resources", json=resource_payload(), headers=h)
    assert r.json()["code"] == "email_not_verified"


async def test_new_users_wait_for_review_trusted_publish(client):
    _, plain = await make_user(role="user")
    _, trusted = await make_user(role="verified_ufazian")
    assert (await make_resource(client, plain))["status"] == "pending_review"
    assert (await make_resource(client, trusted))["status"] == "published"


async def test_author_can_edit_own_but_not_others(client):
    _, a = await make_user(role="verified_ufazian")
    _, b = await make_user(role="verified_ufazian")
    item = await make_resource(client, a)
    ok = await client.patch(
        f"/api/resources/{item['id']}", json={"title": "New title"}, headers=a
    )
    assert ok.status_code == 200 and ok.json()["title"] == "New title"
    no = await client.patch(
        f"/api/resources/{item['id']}", json={"title": "Mine now"}, headers=b
    )
    assert no.status_code == 403
    missing = await client.patch(
        f"/api/resources/{uuid.uuid4()}", json={"title": "Nope nope"}, headers=a
    )
    assert missing.status_code == 404


async def test_hide_requires_a_reason_and_is_audited(client):
    _, owner = await make_user(role="verified_ufazian")
    _, admin = await make_user(role="admin")
    item = await make_resource(client, owner)
    url = f"/api/content/{item['id']}/hide"
    assert (
        await client.post(url, json={"reason": "x"}, headers=admin)
    ).status_code == 422
    assert (
        await client.post(url, json={"reason": "broken and spammy"}, headers=admin)
    ).status_code == 204
    assert (
        await client.get(f"/api/resources/{item['call_number']}")
    ).status_code == 404
    mine = await client.get(f"/api/resources/{item['call_number']}", headers=owner)
    assert mine.json()["hidden_reason"] == "broken and spammy"
    assert (
        await client.post(f"/api/content/{item['id']}/publish", headers=admin)
    ).status_code == 204
    again = await client.get(f"/api/resources/{item['call_number']}")
    assert again.status_code == 200 and again.json()["hidden_reason"] is None
