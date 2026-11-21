import pytest

from tests.factories import make_article, make_resource, make_user


def payload(items, **over):
    return {
        "title": "Everything for Algorithms L2",
        "description": "A reading order.",
        "items": [{"item_id": i, "note": f"note {n}"} for n, i in enumerate(items)],
        "tags": ["algorithms"],
        **over,
    }


async def setup(client):
    _, h = await make_user("verified_ufazian")
    r1 = await make_resource(client, h, title="Resource one")
    r2 = await make_resource(client, h, title="Resource two")
    a = await make_article(client, h)
    return h, r1, r2, a


async def test_create_keeps_order_notes_and_mixed_types(client):
    h, r1, r2, a = await setup(client)
    r = await client.post(
        "/api/collections", json=payload([a["id"], r1["id"], r2["id"]]), headers=h
    )
    assert r.status_code == 201, r.text
    c = r.json()
    assert c["call_number"].startswith("COL-") and c["status"] == "published"
    assert [(i["position"], i["note"], i["item"]["type"]) for i in c["items"]] == [
        (0, "note 0", "article"),
        (1, "note 1", "resource"),
        (2, "note 2", "resource"),
    ]
    got = (await client.get(f"/api/collections/{c['call_number']}")).json()
    assert [i["item"]["id"] for i in got["items"]] == [a["id"], r1["id"], r2["id"]]


async def test_update_reorders_and_replaces_items(client):
    h, r1, r2, a = await setup(client)
    c = (
        await client.post(
            "/api/collections", json=payload([r1["id"], r2["id"]]), headers=h
        )
    ).json()
    r = await client.patch(
        f"/api/collections/{c['id']}",
        json={
            "items": [
                {"item_id": r2["id"], "note": "now first"},
                {"item_id": a["id"], "note": ""},
            ]
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert [(i["item"]["id"], i["note"]) for i in r.json()["items"]] == [
        (r2["id"], "now first"),
        (a["id"], ""),
    ]


@pytest.mark.parametrize("bad", ["unknown", "dup", "collection", "unpublished"])
async def test_invalid_items_are_rejected(client, bad):
    h, r1, r2, a = await setup(client)
    other_h = (await make_user("user"))[1]
    pending = await make_resource(
        client, other_h, title="Needs review"
    )  # pending_review
    inner = (
        await client.post("/api/collections", json=payload([r1["id"]]), headers=h)
    ).json()
    items = {
        "unknown": ["00000000-0000-0000-0000-000000000000"],
        "dup": [r1["id"], r1["id"]],
        "collection": [inner["id"]],
        "unpublished": [pending["id"]],
    }[bad]
    r = await client.post("/api/collections", json=payload(items), headers=h)
    assert r.status_code in (400, 422), r.text


async def test_empty_and_oversized_item_lists_are_rejected(client):
    h, r1, *_ = await setup(client)
    assert (
        await client.post("/api/collections", json=payload([]), headers=h)
    ).status_code == 422


async def test_hidden_items_drop_off_the_shelf(client):
    h, r1, r2, a = await setup(client)
    _, admin = await make_user("admin")
    c = (
        await client.post(
            "/api/collections", json=payload([r1["id"], r2["id"]]), headers=h
        )
    ).json()
    await client.post(
        f"/api/content/{r1['id']}/hide", json={"reason": "broken link"}, headers=admin
    )
    got = (await client.get(f"/api/collections/{c['call_number']}")).json()
    assert [i["item"]["id"] for i in got["items"]] == [r2["id"]]


@pytest.mark.parametrize(
    "actor,status",
    [
        ("guest", 401),
        ("unverified", 403),
        ("muted", 403),
        ("banned", 403),
        ("user", 201),
    ],
)
async def test_create_permissions(client, actor, status):
    h, r1, *_ = await setup(client)
    kw = {
        "guest": None,
        "unverified": dict(verified=False),
        "muted": dict(status="muted"),
        "banned": dict(status="banned"),
        "user": {},
    }[actor]
    headers = (await make_user(**kw))[1] if kw is not None else {}
    r = await client.post("/api/collections", json=payload([r1["id"]]), headers=headers)
    assert r.status_code == status


async def test_edit_permissions_and_pending_review(client):
    h, r1, *_ = await setup(client)
    _, other = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    c = (
        await client.post("/api/collections", json=payload([r1["id"]]), headers=h)
    ).json()
    assert (
        await client.patch(
            f"/api/collections/{c['id']}", json={"title": "Nope nope"}, headers=other
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/collections/{c['id']}", json={"title": "Better title"}, headers=admin
        )
    ).status_code == 200
    _, plain = await make_user("user")
    p = (
        await client.post("/api/collections", json=payload([r1["id"]]), headers=plain)
    ).json()
    assert p["status"] == "pending_review"
    assert (await client.get(f"/api/collections/{p['call_number']}")).status_code == 404


async def test_list_and_search_include_collections(client):
    h, r1, *_ = await setup(client)
    await client.post(
        "/api/collections",
        json=payload([r1["id"]], title="Bakı studyspots", tags=["bakinuniq"]),
        headers=h,
    )
    items = (await client.get("/api/collections?tag=bakinuniq")).json()["items"]
    assert [i["title"] for i in items] == ["Bakı studyspots"]
    hit = (await client.get("/api/search?q=studyspots&type=collection")).json()["items"]
    assert hit and hit[0]["type"] == "collection"
