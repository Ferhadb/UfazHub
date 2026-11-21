import asyncio

import pytest

from tests.factories import make_article, make_resource, make_user


async def post(client, item_id, headers, body="Nice find", parent_id=None):
    return await client.post(
        f"/api/content/{item_id}/comments",
        json={"body": body, "parent_id": parent_id},
        headers=headers,
    )


async def count(client, item):
    key = "articles" if item["type"] == "article" else "resources"
    ref = item.get("slug") or item["call_number"]
    return (await client.get(f"/api/{key}/{ref}")).json()["comment_count"]


async def test_thread_one_level_and_counter(client):
    _, h = await make_user("verified_ufazian")
    _, reader = await make_user("user")
    res = await make_resource(client, h)
    top = (await post(client, res["id"], reader, "Top comment")).json()
    r1 = (await post(client, res["id"], h, "Reply one", top["id"])).json()
    await post(client, res["id"], reader, "Reply two", top["id"])
    deep = await post(client, res["id"], h, "Too deep", r1["id"])
    assert deep.status_code == 422 and deep.json()["code"] == "reply_too_deep"
    assert await count(client, res) == 3
    page = (await client.get(f"/api/content/{res['id']}/comments")).json()
    assert len(page["items"]) == 1 and page["next_cursor"] is None
    assert [r["body"] for r in page["items"][0]["replies"]] == [
        "Reply one",
        "Reply two",
    ]
    assert page["items"][0]["author"]["display_name"]


async def test_works_on_articles_too_and_html_stays_text(client):
    _, h = await make_user("verified_ufazian")
    a = await make_article(client, h)
    c = (await post(client, a["id"], h, "<script>alert(1)</script>")).json()
    assert (
        c["body"] == "<script>alert(1)</script>"
    )  # stored as text; the UI renders it as text
    assert await count(client, a) == 1


async def test_delete_removes_replies_and_fixes_counter(client):
    _, h = await make_user("verified_ufazian")
    _, reader = await make_user("user")
    res = await make_resource(client, h)
    top = (await post(client, res["id"], reader)).json()
    await post(client, res["id"], h, "r", top["id"])
    await post(client, res["id"], h, "r2", top["id"])
    keep = (await post(client, res["id"], h, "other")).json()
    assert await count(client, res) == 4
    assert (
        await client.delete(f"/api/comments/{top['id']}", headers=h)
    ).status_code == 403
    assert (
        await client.delete(f"/api/comments/{top['id']}", headers=reader)
    ).status_code == 204
    assert await count(client, res) == 1
    page = (await client.get(f"/api/content/{res['id']}/comments")).json()["items"]
    assert [c["id"] for c in page] == [keep["id"]]
    assert (
        await client.delete(f"/api/comments/{top['id']}", headers=reader)
    ).status_code == 404


async def test_admin_delete_is_audited(client):
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.audit import AuditLog

    _, h = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    res = await make_resource(client, h)
    c = (await post(client, res["id"], h, "spam")).json()
    assert (
        await client.delete(f"/api/comments/{c['id']}", headers=admin)
    ).status_code == 204
    async with SessionLocal() as db:
        row = (
            await db.execute(select(AuditLog).where(AuditLog.target_id == c["id"]))
        ).scalar_one()
    assert row.action == "comment.delete"


async def test_concurrent_comments_keep_the_counter_exact(client):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    users = [(await make_user())[1] for _ in range(8)]
    rs = await asyncio.gather(
        *[post(client, res["id"], u, f"c{i}") for i, u in enumerate(users)]
    )
    assert all(r.status_code == 201 for r in rs)
    assert await count(client, res) == 8
    top = rs[0].json()
    rs = await asyncio.gather(
        *[post(client, res["id"], u, "r", top["id"]) for u in users]
    )
    assert all(r.status_code == 201 for r in rs)
    assert await count(client, res) == 16


async def test_reply_cap(client, monkeypatch):
    from app.services import comments

    monkeypatch.setattr(comments, "MAX_REPLIES", 2)
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    top = (await post(client, res["id"], h)).json()
    for _ in range(2):
        assert (await post(client, res["id"], h, "r", top["id"])).status_code == 201
    full = await post(client, res["id"], h, "r", top["id"])
    assert full.status_code == 409 and full.json()["code"] == "thread_full"


async def test_parent_must_belong_to_the_same_item(client):
    _, h = await make_user("verified_ufazian")
    a, b = await make_resource(client, h), await make_resource(client, h)
    top = (await post(client, a["id"], h)).json()
    assert (await post(client, b["id"], h, "x", top["id"])).status_code == 404


async def test_pagination(client):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    ids = [(await post(client, res["id"], h, f"c{i}")).json()["id"] for i in range(5)]
    seen, cursor = [], ""
    while True:
        page = (
            await client.get(f"/api/content/{res['id']}/comments?limit=2{cursor}")
        ).json()
        seen += [c["id"] for c in page["items"]]
        if not page["next_cursor"]:
            break
        cursor = f"&cursor={page['next_cursor']}"
    assert seen == ids
    assert (
        await client.get(f"/api/content/{res['id']}/comments?cursor=zzz")
    ).status_code == 400


async def test_unpublished_items_have_no_comments(client):
    _, h = await make_user("verified_ufazian")
    d = await make_article(client, h, publish=False)
    assert (await post(client, d["id"], h)).status_code == 404
    assert (await client.get(f"/api/content/{d['id']}/comments")).status_code == 404


@pytest.mark.parametrize(
    "actor,status",
    [
        ("guest", 401),
        ("unverified", 403),
        ("muted", 403),
        ("banned", 403),
        ("user", 201),
        ("admin", 201),
    ],
)
async def test_permissions(client, actor, status):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    kw = {
        "guest": None,
        "unverified": dict(verified=False),
        "muted": dict(status="muted"),
        "banned": dict(status="banned"),
        "user": {},
        "admin": dict(role="admin"),
    }[actor]
    headers = (await make_user(**kw))[1] if kw is not None else {}
    assert (await post(client, res["id"], headers)).status_code == status


async def test_validation_and_rate_limit(client):
    _, h = await make_user("verified_ufazian")
    res = await make_resource(client, h)
    assert (await post(client, res["id"], h, "   ")).status_code == 422
    assert (await post(client, res["id"], h, "x" * 2001)).status_code == 422
    codes = [(await post(client, res["id"], h)).status_code for _ in range(12)]
    assert (
        codes.count(201) == 8 and codes[-1] == 429
    )  # the two invalid posts above count too
