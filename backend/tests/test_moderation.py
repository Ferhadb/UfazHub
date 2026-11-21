"""Reports, queue, admin content/user actions, appeals, history, audit log."""

import uuid

import pytest
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.audit import AuditLog
from tests.factories import make_article, make_resource, make_user
from tests.test_auth import PW, csrf, login, signup

A = "/api/admin"


async def audit_rows(action: str, target_id) -> list[AuditLog]:
    async with SessionLocal() as db:
        return list(
            await db.scalars(
                select(AuditLog).where(
                    AuditLog.action == action, AuditLog.target_id == str(target_id)
                )
            )
        )


async def act(client, admin, ids, action, reason="not suitable here"):
    r = await client.post(
        f"{A}/content/actions",
        json={"ids": ids, "action": action, "reason": reason},
        headers=admin,
    )
    assert r.status_code == 200, r.text
    return r.json()


async def setup():
    owner, oh = await make_user(role="verified_ufazian")
    admin_user, admin = await make_user(role="admin")
    reporter, rh = await make_user()
    return owner, oh, admin_user, admin, reporter, rh


# --- reports ------------------------------------------------------------------------
async def test_report_rules(client):
    _, oh, _, _, _, rh = await setup()
    item = await make_resource(client, oh)
    url = f"/api/content/{item['id']}/report"
    body = {"reason": "spam", "note": " looks like an ad "}
    assert (await client.post(url, json=body)).status_code == 401
    assert (await client.post(url, json=body, headers=oh)).status_code == 403  # own
    assert (
        await client.post(url, json={"reason": "nope"}, headers=rh)
    ).status_code == 422
    assert (await client.post(url, json=body, headers=rh)).status_code == 204
    dup = await client.post(url, json=body, headers=rh)
    assert dup.status_code == 409 and dup.json()["code"] == "already_reported"
    _, muted = await make_user(status="muted")
    assert (await client.post(url, json=body, headers=muted)).status_code == 403
    _, unverified = await make_user(verified=False)
    assert (await client.post(url, json=body, headers=unverified)).status_code == 403
    missing = await client.post(
        f"/api/content/{uuid.uuid4()}/report", json=body, headers=rh
    )
    assert missing.status_code == 404


async def test_report_button_works_for_every_content_type(client):
    _, oh, _, _, _, rh = await setup()
    article = await make_article(client, oh)
    r = await client.post(
        f"/api/content/{article['id']}/report", json={"reason": "other"}, headers=rh
    )
    assert r.status_code == 204


async def test_cannot_report_what_you_cannot_see(client):
    _, _, _, admin, _, rh = await setup()
    _, plain = await make_user(role="user")
    pending = await make_resource(client, plain)
    assert pending["status"] == "pending_review"
    r = await client.post(
        f"/api/content/{pending['id']}/report", json={"reason": "spam"}, headers=rh
    )
    assert r.status_code == 404


# --- queue ----------------------------------------------------------------------------
async def test_queue_filters_and_pagination(client):
    _, oh, _, admin, _, rh = await setup()
    _, rh2 = await make_user()
    spam = await make_resource(client, oh)
    off = await make_article(client, oh)
    for who, item, reason in (
        (rh, spam, "spam"),
        (rh2, spam, "offensive"),
        (rh, off, "offensive"),
    ):
        r = await client.post(
            f"/api/content/{item['id']}/report", json={"reason": reason}, headers=who
        )
        assert r.status_code == 204
    q = (await client.get(f"{A}/queue", headers=admin)).json()
    by_id = {i["id"]: i for i in q["items"]}
    assert by_id[spam["id"]]["report_count"] == 2
    assert by_id[spam["id"]]["reasons"] == ["offensive", "spam"]
    only_off = (
        await client.get(f"{A}/queue?reason=offensive&type=article", headers=admin)
    ).json()["items"]
    assert [i["id"] for i in only_off] == [off["id"]]
    p1 = (await client.get(f"{A}/queue?limit=1", headers=admin)).json()
    p2 = (
        await client.get(f"{A}/queue?limit=1&cursor={p1['next_cursor']}", headers=admin)
    ).json()
    assert p1["items"][0]["id"] != p2["items"][0]["id"]
    bad = await client.get(f"{A}/queue?cursor=zzz", headers=admin)
    assert bad.status_code == 400


async def test_pending_and_hidden_views(client):
    _, oh, _, admin, _, _ = await setup()
    _, plain = await make_user(role="user")
    pending = await make_resource(client, plain)
    shown = await make_resource(client, oh)
    await act(client, admin, [shown["id"]], "hide")
    pend = (await client.get(f"{A}/queue?view=pending", headers=admin)).json()["items"]
    hid = (await client.get(f"{A}/queue?view=hidden", headers=admin)).json()["items"]
    assert pending["id"] in {i["id"] for i in pend}
    assert shown["id"] in {i["id"] for i in hid}


# --- content actions -------------------------------------------------------------------
async def test_hide_unhide_approve_dismiss_with_audit(client):
    owner, oh, admin_user, admin, _, rh = await setup()
    _, plain = await make_user(role="user")
    item = await make_resource(client, oh)
    await client.post(
        f"/api/content/{item['id']}/report", json={"reason": "spam"}, headers=rh
    )

    # dismiss closes the report, leaves the item alone
    out = await act(client, admin, [item["id"]], "dismiss", "fine")
    assert out["done"] == [item["id"]]
    assert (await audit_rows("report.dismiss", item["id"]))[0].before == {
        "open_reports": 1
    }
    again = await act(client, admin, [item["id"]], "dismiss")
    assert again["failed"][0]["message"].startswith("There are no open reports")

    # hide: reports are actioned, the author is told, diff is stored
    _, rh2 = await make_user()
    await client.post(
        f"/api/content/{item['id']}/report", json={"reason": "spam"}, headers=rh2
    )
    await act(client, admin, [item["id"]], "hide", "spam link")
    (row,) = await audit_rows("content.hide", item["id"])
    assert row.actor_id == admin_user.id and row.reason == "spam link"
    assert row.before == {"status": "published", "hidden_reason": None}
    assert row.after == {"status": "hidden", "hidden_reason": "spam link"}
    queue = (await client.get(f"{A}/queue", headers=admin)).json()["items"]
    assert item["id"] not in {i["id"] for i in queue}
    notes = (await client.get("/api/notifications", headers=oh)).json()["items"]
    assert notes[0]["kind"] == "moderation" and notes[0]["message"] == "spam link"
    again = await act(client, admin, [item["id"]], "hide")
    assert again["failed"] and not again["done"]

    # unhide
    await act(client, admin, [item["id"]], "unhide", "mistake")
    (row,) = await audit_rows("content.unhide", item["id"])
    assert row.before["status"] == "hidden" and row.after["status"] == "published"
    assert (
        await client.get(f"/api/resources/{item['call_number']}")
    ).status_code == 200

    # approve a pending item
    pending = await make_resource(client, plain)
    await act(client, admin, [pending["id"]], "approve", None)
    (row,) = await audit_rows("content.approve", pending["id"])
    assert row.before["status"] == "pending_review"
    bad = await act(client, admin, [pending["id"]], "approve", None)
    assert bad["failed"]


async def test_bulk_is_partial_and_validated(client):
    _, oh, _, admin, _, _ = await setup()
    a, b = await make_resource(client, oh), await make_resource(client, oh)
    ghost = str(uuid.uuid4())
    out = await act(client, admin, [a["id"], ghost, b["id"]], "hide", "cleanup now")
    assert out["done"] == [a["id"], b["id"]]
    assert out["failed"][0]["id"] == ghost
    post = lambda body: client.post(  # noqa: E731
        f"{A}/content/actions", json=body, headers=admin
    )
    assert (await post({"ids": [a["id"]], "action": "hide"})).status_code == 422
    assert (await post({"ids": [], "action": "approve"})).status_code == 422
    assert (
        await post({"ids": [a["id"], a["id"]], "action": "approve"})
    ).status_code == 422
    assert (await post({"ids": [a["id"]], "action": "delete"})).status_code == 422


async def test_legacy_hide_and_publish_routes_use_the_same_audit(client):
    _, oh, _, admin, _, _ = await setup()
    item = await make_resource(client, oh)
    url = f"/api/content/{item['id']}"
    assert (
        await client.post(f"{url}/hide", json={"reason": "off topic"}, headers=admin)
    ).status_code == 204
    assert (await client.post(f"{url}/publish", headers=admin)).status_code == 204
    assert (await client.post(f"{url}/publish", headers=admin)).status_code == 204
    assert await audit_rows("content.unhide", item["id"])


# --- admin permissions -------------------------------------------------------------------
@pytest.mark.parametrize(
    "who,expected",
    [
        ("guest", 401),
        ("user", 403),
        ("verified", 403),
        ("muted_admin", 403),
        ("admin", 200),
    ],
)
async def test_admin_endpoints_are_admin_only(client, who, expected):
    headers = {
        "guest": None,
        "user": (await make_user())[1],
        "verified": (await make_user(role="verified_ufazian"))[1],
        "muted_admin": (await make_user(role="admin", status="muted"))[1],
        "admin": (await make_user(role="admin"))[1],
    }[who]
    for path in ("/queue", "/users", "/appeals", "/audit"):
        r = await client.get(A + path, headers=headers)
        assert r.status_code == expected, (path, r.text)
    r = await client.post(
        f"{A}/content/actions",
        json={"ids": [str(uuid.uuid4())], "action": "dismiss"},
        headers=headers,
    )
    assert r.status_code == (200 if expected == 200 else expected)
    uid = uuid.uuid4()
    r = await client.put(
        f"{A}/users/{uid}/status",
        json={"status": "muted", "reason": "testing"},
        headers=headers,
    )
    assert r.status_code == (404 if expected == 200 else expected)
    r = await client.put(
        f"{A}/users/{uid}/role",
        json={"role": "admin", "reason": "testing"},
        headers=headers,
    )
    assert r.status_code == (404 if expected == 200 else expected)


# --- user actions --------------------------------------------------------------------------
async def test_mute_blocks_writes_and_is_audited(client):
    admin_user, admin = await make_user(role="admin")
    target, th = await make_user(role="verified_ufazian")
    url = f"{A}/users/{target.id}/status"
    assert (
        await client.put(url, json={"status": "muted", "reason": "x"}, headers=admin)
    ).status_code == 422
    r = await client.put(
        url, json={"status": "muted", "reason": "heated arguments"}, headers=admin
    )
    assert r.status_code == 200 and r.json()["status"] == "muted"
    (row,) = await audit_rows("user.mute", target.id)
    assert row.before == {"status": "active"} and row.after == {"status": "muted"}
    assert row.reason == "heated arguments" and row.actor_id == admin_user.id
    blocked = await client.post(
        "/api/resources",
        json={"title": "x" * 5, "resource_type": "book"},
        headers=th,
    )
    assert blocked.status_code == 403 and blocked.json()["code"] == "account_muted"
    assert (
        await client.put(
            url, json={"status": "muted", "reason": "again"}, headers=admin
        )
    ).status_code == 409
    r = await client.put(
        url, json={"status": "active", "reason": "apologised"}, headers=admin
    )
    assert r.status_code == 200
    assert await audit_rows("user.unmute", target.id)


async def test_ban_ends_sessions_and_blocks_login_until_unban(client):
    _, admin = await make_user(role="admin")
    email, r = await signup(client)
    assert r.status_code == 201
    user_id = r.json()["id"]
    r = await login(client, email)
    token = {"Authorization": f"Bearer {r.json()['access_token']}"}
    headers = csrf(client)
    url = f"{A}/users/{user_id}/status"
    r = await client.put(
        url, json={"status": "banned", "reason": "repeated abuse"}, headers=admin
    )
    assert r.status_code == 200
    assert (await audit_rows("user.ban", user_id))[0].after == {"status": "banned"}
    assert (await client.get("/api/auth/me", headers=token)).status_code == 403
    refreshed = await client.post("/api/auth/refresh", headers=headers)
    assert refreshed.status_code == 401
    r = await login(client, email)
    assert r.status_code == 403 and r.json()["code"] == "account_banned"
    r = await client.put(
        url, json={"status": "active", "reason": "appeal upheld"}, headers=admin
    )
    assert r.status_code == 200 and await audit_rows("user.unban", user_id)
    assert (await login(client, email)).status_code == 200


async def test_role_change_and_guards(client):
    admin_user, admin = await make_user(role="admin")
    other_admin, _ = await make_user(role="admin")
    target, th = await make_user()
    r = await client.put(
        f"{A}/users/{target.id}/role",
        json={"role": "verified_ufazian", "reason": "confirmed student"},
        headers=admin,
    )
    assert r.status_code == 200 and r.json()["role"] == "verified_ufazian"
    (row,) = await audit_rows("user.role", target.id)
    assert row.before == {"role": "user"} and row.after == {"role": "verified_ufazian"}
    same = await client.put(
        f"{A}/users/{target.id}/role",
        json={"role": "verified_ufazian", "reason": "again"},
        headers=admin,
    )
    assert same.status_code == 409
    bad = await client.put(
        f"{A}/users/{target.id}/role",
        json={"role": "root", "reason": "hmm"},
        headers=admin,
    )
    assert bad.status_code == 422
    me = await client.put(
        f"{A}/users/{admin_user.id}/role",
        json={"role": "user", "reason": "oops"},
        headers=admin,
    )
    assert me.status_code == 403 and me.json()["code"] == "self_action"
    ban_admin = await client.put(
        f"{A}/users/{other_admin.id}/status",
        json={"status": "banned", "reason": "no way"},
        headers=admin,
    )
    assert ban_admin.status_code == 409


async def test_user_list_filters(client):
    _, admin = await make_user(role="admin")
    u, _ = await make_user(name="Zorblax Findme", status="muted")
    r = await client.get(f"{A}/users?q=zorblax&status=muted", headers=admin)
    assert [x["id"] for x in r.json()["items"]] == [str(u.id)]
    r = await client.get(f"{A}/users?q=100%25", headers=admin)  # wildcard is literal
    assert r.json()["items"] == []
    r = await client.get(f"{A}/users?limit=1", headers=admin)
    assert r.json()["next_cursor"]


# --- appeals + history -----------------------------------------------------------------------
async def test_content_appeal_accepted_and_history(client):
    owner, oh, _, admin, _, _ = await setup()
    item = await make_resource(client, oh)
    await act(client, admin, [item["id"]], "hide", "looks like spam")
    hist = (await client.get("/api/me/moderation", headers=oh)).json()["items"]
    assert (
        hist[0]["action"] == "content.hide" and hist[0]["reason"] == "looks like spam"
    )
    assert hist[0]["item"]["call_number"] == item["call_number"]
    assert "actor" not in hist[0]
    other = (await client.get("/api/me/moderation", headers=admin)).json()["items"]
    assert other == []

    url = f"/api/content/{item['id']}/appeal"
    _, stranger = await make_user()
    assert (
        await client.post(
            url, json={"message": "this is mine, honest"}, headers=stranger
        )
    ).status_code == 404
    assert (
        await client.post(url, json={"message": "short"}, headers=oh)
    ).status_code == 422
    ok = await client.post(
        url, json={"message": "It is a legitimate resource"}, headers=oh
    )
    assert ok.status_code == 204
    dup = await client.post(
        url, json={"message": "It is a legitimate resource"}, headers=oh
    )
    assert dup.status_code == 409 and dup.json()["code"] == "appeal_open"

    mine = (await client.get("/api/me/appeals", headers=oh)).json()["items"]
    assert mine[0]["status"] == "open" and mine[0]["item"]["id"] == item["id"]
    queue = (await client.get(f"{A}/appeals", headers=admin)).json()["items"]
    appeal = next(a for a in queue if a["id"] == mine[0]["id"])
    res = f"{A}/appeals/{appeal['id']}/resolve"
    assert (
        await client.post(
            res, json={"decision": "accept", "response": "ok"}, headers=oh
        )
    ).status_code == 403
    r = await client.post(
        res,
        json={"decision": "accept", "response": "Checked, it is fine."},
        headers=admin,
    )
    assert r.status_code == 204
    assert (
        await client.get(f"/api/resources/{item['call_number']}")
    ).status_code == 200
    assert (await audit_rows("appeal.accept", appeal["id"]))[0].after == {
        "status": "accepted"
    }
    assert await audit_rows("content.unhide", item["id"])
    mine = (await client.get("/api/me/appeals", headers=oh)).json()["items"]
    assert (
        mine[0]["status"] == "accepted"
        and mine[0]["response"] == "Checked, it is fine."
    )
    closed = await client.post(
        res, json={"decision": "reject", "response": "too late"}, headers=admin
    )
    assert closed.status_code == 409
    still_open = (await client.get(f"{A}/appeals", headers=admin)).json()["items"]
    assert appeal["id"] not in {a["id"] for a in still_open}


async def test_content_appeal_rejected_keeps_item_hidden_and_allows_retry(client):
    _, oh, _, admin, _, _ = await setup()
    item = await make_resource(client, oh)
    url = f"/api/content/{item['id']}/appeal"
    msg = {"message": "Please look again at this"}
    assert (
        await client.post(url, json=msg, headers=oh)
    ).status_code == 409  # not hidden
    await act(client, admin, [item["id"]], "hide")
    await client.post(url, json=msg, headers=oh)
    open_ = (await client.get(f"{A}/appeals", headers=admin)).json()["items"]
    (a,) = [x for x in open_ if x["item"]["id"] == item["id"]]
    r = await client.post(
        f"{A}/appeals/{a['id']}/resolve",
        json={"decision": "reject", "response": "Still spam."},
        headers=admin,
    )
    assert r.status_code == 204
    assert (
        await client.get(f"/api/resources/{item['call_number']}")
    ).status_code == 404
    notes = (await client.get("/api/notifications", headers=oh)).json()["items"]
    assert notes[0]["message"] == "Appeal rejected: Still spam."
    assert (await client.post(url, json=msg, headers=oh)).status_code == 204
    rejected = (await client.get(f"{A}/appeals?status=rejected", headers=admin)).json()
    assert a["id"] in {x["id"] for x in rejected["items"]}


async def test_muted_author_can_still_appeal(client):
    owner, oh, _, admin, _, _ = await setup()
    item = await make_resource(client, oh)
    await act(client, admin, [item["id"]], "hide")
    await client.put(
        f"{A}/users/{owner.id}/status",
        json={"status": "muted", "reason": "cool down"},
        headers=admin,
    )
    r = await client.post(
        f"/api/content/{item['id']}/appeal",
        json={"message": "Please reconsider this"},
        headers=oh,
    )
    assert r.status_code == 204
    kinds = {
        e["action"]
        for e in (await client.get("/api/me/moderation", headers=oh)).json()["items"]
    }
    assert kinds == {"content.hide", "user.mute"}


async def test_ban_appeal_flow(client):
    _, admin = await make_user(role="admin")
    email, r = await signup(client)
    user_id = r.json()["id"]
    url = "/api/auth/appeal"
    body = {"email": email, "password": PW, "message": "I will behave from now on"}
    assert (await client.post(url, json=body)).status_code == 409  # not banned yet
    await client.put(
        f"{A}/users/{user_id}/status",
        json={"status": "banned", "reason": "abuse of reports"},
        headers=admin,
    )
    wrong = await client.post(url, json={**body, "password": "wrong password"})
    assert wrong.status_code == 401
    assert (await client.post(url, json=body)).status_code == 204
    assert (await client.post(url, json=body)).status_code == 409
    open_ = (await client.get(f"{A}/appeals", headers=admin)).json()["items"]
    (a,) = [x for x in open_ if x["user"]["id"] == user_id]
    assert a["kind"] == "ban" and a["item"] is None
    r = await client.post(
        f"{A}/appeals/{a['id']}/resolve",
        json={"decision": "accept", "response": "Welcome back."},
        headers=admin,
    )
    assert r.status_code == 204
    assert (await login(client, email)).status_code == 200
    assert await audit_rows("user.unban", user_id)


# --- audit log viewer ---------------------------------------------------------------------------
async def test_audit_log_filters_and_paging(client):
    admin_user, admin = await make_user(role="admin")
    _, oh = await make_user(role="verified_ufazian")
    item = await make_resource(client, oh)
    await act(client, admin, [item["id"]], "hide")
    await act(client, admin, [item["id"]], "unhide")
    r = (
        await client.get(
            f"{A}/audit?target_type=content_item&target_id={item['id']}", headers=admin
        )
    ).json()
    assert [e["action"] for e in r["items"]] == ["content.unhide", "content.hide"]
    assert r["items"][0]["actor"]["id"] == str(admin_user.id)
    assert r["items"][1]["before"]["status"] == "published"
    only = (
        await client.get(
            f"{A}/audit?action=content.hide&actor_id={admin_user.id}", headers=admin
        )
    ).json()
    assert all(e["action"] == "content.hide" for e in only["items"])
    p1 = (await client.get(f"{A}/audit?limit=1", headers=admin)).json()
    p2 = (
        await client.get(f"{A}/audit?limit=1&cursor={p1['next_cursor']}", headers=admin)
    ).json()
    assert p1["items"][0]["id"] != p2["items"][0]["id"]
    assert (
        await client.get(f"{A}/audit?actor_id=nope", headers=admin)
    ).status_code == 422
