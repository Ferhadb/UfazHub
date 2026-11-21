import uuid

from tests.factories import (
    make_article,
    make_question,
    make_resource,
    make_user,
)


async def test_research_lists_flagged_items_across_types(client):
    _, h = await make_user("verified_ufazian")
    tag = "rs" + uuid.uuid4().hex[:6]
    res = await make_resource(client, h, is_research=True, tags=[tag])
    art = await make_article(client, h, is_research=True, tags=[tag])
    await make_resource(client, h, tags=[tag])  # not research
    q = await make_question(client, h, tags=[tag])  # questions cannot be flagged
    r = (await client.get("/api/research", params={"tag": tag})).json()
    assert {i["id"] for i in r["items"]} == {res["id"], art["id"]}
    assert {i["type"] for i in r["items"]} == {"resource", "article"}
    only = (
        await client.get("/api/research", params={"tag": tag, "type": "article"})
    ).json()
    assert [i["id"] for i in only["items"]] == [art["id"]]
    assert q["id"] not in {i["id"] for i in r["items"]}
    page = (await client.get("/api/research", params={"tag": tag, "limit": 1})).json()
    assert page["next_cursor"]
    nxt = (
        await client.get(
            "/api/research",
            params={"tag": tag, "limit": 1, "cursor": page["next_cursor"]},
        )
    ).json()
    assert (
        nxt["items"][0]["id"] != page["items"][0]["id"] and nxt["next_cursor"] is None
    )


async def test_follow_tags_and_for_you_feed(client):
    _, author = await make_user("verified_ufazian")
    _, me = await make_user("verified_ufazian")
    t1, t2 = "fy" + uuid.uuid4().hex[:6], "fy" + uuid.uuid4().hex[:6]
    followed = await make_resource(client, author, tags=[t1])
    await make_resource(client, author, tags=[t2])
    mine = await make_resource(client, me, tags=[t1])

    assert (await client.get("/api/feed/for-you")).status_code == 401
    assert (await client.get("/api/feed/for-you", headers=me)).json()["items"] == []
    assert (await client.put(f"/api/tags/{t1}/follow", headers=me)).json() == {
        "following": True
    }
    await client.put(f"/api/tags/{t1}/follow", headers=me)  # idempotent
    assert [
        t["slug"] for t in (await client.get("/api/me/tags", headers=me)).json()
    ] == [t1]
    feed = (await client.get("/api/feed/for-you", headers=me)).json()["items"]
    assert [i["id"] for i in feed] == [followed["id"]]  # not t2, not my own post
    assert mine["id"] not in {i["id"] for i in feed}
    assert (await client.delete(f"/api/tags/{t1}/follow", headers=me)).json() == {
        "following": False
    }
    assert (await client.get("/api/feed/for-you", headers=me)).json()["items"] == []
    assert (
        await client.put("/api/tags/nope-nope/follow", headers=me)
    ).status_code == 404
    assert (await client.put(f"/api/tags/{t1}/follow")).status_code == 401


async def test_follow_cap(client, monkeypatch):
    from app.services import follows

    monkeypatch.setattr(follows, "MAX_FOLLOWS", 1)
    _, h = await make_user("verified_ufazian")
    a, b = "cap" + uuid.uuid4().hex[:6], "cap" + uuid.uuid4().hex[:6]
    await make_resource(client, h, tags=[a, b])
    assert (await client.put(f"/api/tags/{a}/follow", headers=h)).status_code == 200
    assert (await client.put(f"/api/tags/{a}/follow", headers=h)).status_code == 200
    r = await client.put(f"/api/tags/{b}/follow", headers=h)
    assert r.status_code == 409 and r.json()["code"] == "follow_limit"


async def test_bookmarks_list_newest_first_and_skips_hidden(client):
    _, ah = await make_user("admin")
    _, h = await make_user("verified_ufazian")
    _, me = await make_user("user")
    first = await make_resource(client, h)
    second = await make_article(client, h)
    gone = await make_resource(client, h)
    for it in (first, second, gone):
        await client.put(f"/api/content/{it['id']}/bookmark", headers=me)
    await client.post(
        f"/api/content/{gone['id']}/hide", json={"reason": "stale"}, headers=ah
    )
    got = (await client.get("/api/me/bookmarks", headers=me)).json()
    assert [i["id"] for i in got["items"]] == [second["id"], first["id"]]
    p1 = (await client.get("/api/me/bookmarks?limit=1", headers=me)).json()
    p2 = (
        await client.get(
            f"/api/me/bookmarks?limit=1&cursor={p1['next_cursor']}", headers=me
        )
    ).json()
    assert [p1["items"][0]["id"], p2["items"][0]["id"]] == [second["id"], first["id"]]
    assert (await client.get("/api/me/bookmarks")).status_code == 401


async def test_reading_lists_are_private_until_shared(client):
    _, h = await make_user("verified_ufazian")
    _, me = await make_user("user", name="Reader")
    _, other = await make_user("user")
    res = await make_resource(client, h)
    art = await make_article(client, h)
    r = await client.post(
        "/api/me/reading-lists", json={"name": "Exam week"}, headers=me
    )
    assert r.status_code == 201 and r.json()["share_token"] is None
    lid = r.json()["id"]
    await client.put(f"/api/reading-lists/{lid}/items/{res['id']}", headers=me)
    out = await client.put(f"/api/reading-lists/{lid}/items/{art['id']}", headers=me)
    assert out.json()["item_count"] == 2
    again = await client.put(f"/api/reading-lists/{lid}/items/{art['id']}", headers=me)
    assert again.json()["item_count"] == 2  # idempotent

    items = (await client.get(f"/api/reading-lists/{lid}/items", headers=me)).json()
    assert [i["id"] for i in items["items"]] == [art["id"], res["id"]]
    # someone else's list looks missing; so does every write to it
    for method, url in [
        ("get", f"/api/reading-lists/{lid}/items"),
        ("put", f"/api/reading-lists/{lid}/items/{res['id']}"),
        ("delete", f"/api/reading-lists/{lid}"),
        ("put", f"/api/reading-lists/{lid}/share"),
    ]:
        assert (await client.request(method, url, headers=other)).status_code == 404

    token = (await client.put(f"/api/reading-lists/{lid}/share", headers=me)).json()[
        "share_token"
    ]
    assert (
        token
        and (await client.put(f"/api/reading-lists/{lid}/share", headers=me)).json()[
            "share_token"
        ]
        == token
    )  # stable while shared
    shared = await client.get(f"/api/shared/lists/{token}")  # no sign-in needed
    assert shared.status_code == 200
    body = shared.json()
    assert body["name"] == "Exam week" and body["owner"]["display_name"] == "Reader"
    assert "email" not in body["owner"]
    assert [i["id"] for i in body["items"]] == [art["id"], res["id"]]

    await client.delete(f"/api/reading-lists/{lid}/share", headers=me)
    assert (await client.get(f"/api/shared/lists/{token}")).status_code == 404
    assert (await client.get("/api/shared/lists/nope")).status_code == 404

    renamed = await client.patch(
        f"/api/reading-lists/{lid}", json={"name": "Finals"}, headers=me
    )
    assert renamed.json()["name"] == "Finals"
    await client.delete(f"/api/reading-lists/{lid}/items/{res['id']}", headers=me)
    mine = (await client.get("/api/me/reading-lists", headers=me)).json()["items"]
    assert [(m["name"], m["item_count"]) for m in mine] == [("Finals", 1)]
    assert (
        await client.delete(f"/api/reading-lists/{lid}", headers=me)
    ).status_code == 204
    assert (await client.get("/api/me/reading-lists", headers=me)).json()["items"] == []


async def test_reading_list_validation_and_caps(client, monkeypatch):
    from app.services import readinglists

    monkeypatch.setattr(readinglists, "MAX_LISTS", 1)
    monkeypatch.setattr(readinglists, "MAX_ITEMS", 1)
    _, h = await make_user("verified_ufazian")
    _, me = await make_user("user")
    res, res2 = await make_resource(client, h), await make_resource(client, h)
    assert (
        await client.post("/api/me/reading-lists", json={"name": "  "}, headers=me)
    ).status_code == 422
    assert (
        await client.post("/api/me/reading-lists", json={"name": "A"})
    ).status_code == 401
    lid = (
        await client.post("/api/me/reading-lists", json={"name": "A"}, headers=me)
    ).json()["id"]
    full = await client.post("/api/me/reading-lists", json={"name": "B"}, headers=me)
    assert full.status_code == 409 and full.json()["code"] == "list_limit"
    await client.put(f"/api/reading-lists/{lid}/items/{res['id']}", headers=me)
    r = await client.put(f"/api/reading-lists/{lid}/items/{res2['id']}", headers=me)
    assert r.status_code == 409 and r.json()["code"] == "list_full"
    missing = await client.put(
        f"/api/reading-lists/{lid}/items/{uuid.uuid4()}", headers=me
    )
    assert missing.status_code == 404
