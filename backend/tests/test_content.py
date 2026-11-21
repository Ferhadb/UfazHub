import asyncio
import re
import uuid

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.urls import canonical_url
from app.db.session import SessionLocal
from app.models.content import Bookmark, ContentItem, Vote
from tests.factories import make_resource, make_user, resource_payload


def uniq() -> str:
    return "zq" + uuid.uuid4().hex[:10]


# --- canonical URLs ------------------------------------------------------------------------
@pytest.mark.parametrize(
    "raw",
    [
        "http://www.Example.org/a/b/?utm_source=x&b=2&a=1#frag",
        "https://example.org:443/a/b?a=1&b=2&fbclid=zzz",
        "HTTPS://EXAMPLE.org/a/b/?a=1&b=2",
    ],
)
def test_canonical_url_collapses_spellings(raw):
    assert canonical_url(raw) == "https://example.org/a/b?a=1&b=2"


@pytest.mark.parametrize(
    "bad",
    [
        "javascript:alert(1)",
        "ftp://x.org/a",
        "https://user:pw@x.org",
        "https://localhost",
        "//x.org",
        "",
    ],
)
def test_canonical_url_rejects_unsafe(bad):
    with pytest.raises(ValueError):
        canonical_url(bad)


# --- create / read ------------------------------------------------------------------------------
async def test_create_and_fetch_resource(client):
    _, h = await make_user(role="verified_ufazian", name="Aygün")
    item = await make_resource(
        client,
        h,
        tags=["Algebra", "  algebra ", "Əlgəbr", "Past Exams"],
        links=[
            {"url": "https://example.org/a?utm_source=x", "label": "Main"},
            {"url": "http://www.example.org/a/", "label": "dup"},
            {"url": "https://example.org/b", "label": "Mirror"},
        ],
        is_research=True,
        warning="Chapter 3 has errata.",
    )
    assert re.fullmatch(r"RES-\d{4,}", item["call_number"])
    assert item["author"]["display_name"] == "Aygün" and "email" not in item["author"]
    assert item["tags"] == ["Algebra", "Past Exams", "Əlgəbr"] or len(item["tags"]) == 3
    assert [link["label"] for link in item["links"]] == [
        "Main",
        "Mirror",
    ]  # duplicate dropped
    assert (
        item["vote_score"] == 0
        and item["is_research"]
        and item["status"] == "published"
    )
    got = await client.get(f"/api/resources/{item['call_number'].lower()}")
    assert got.status_code == 200 and got.json()["id"] == item["id"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("title", "ab"),
        ("description", "short"),
        ("resource_type", "movie"),
        ("difficulty", "expert"),
        ("links", []),
        ("links", [{"url": "javascript:alert(1)"}]),
        ("tags", [f"t{i}" for i in range(9)]),
        ("time_commitment_minutes", -1),
    ],
)
async def test_create_validation(client, field, value):
    _, h = await make_user(role="verified_ufazian")
    r = await client.post(
        "/api/resources", json=resource_payload(**{field: value}), headers=h
    )
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


async def test_control_characters_are_stripped(client):
    _, h = await make_user(role="verified_ufazian")
    item = await make_resource(client, h, title="Clean\x02 title\x03 here")
    assert item["title"] == "Clean title here"


async def test_db_constraints_hold(client):
    _, h = await make_user(role="verified_ufazian")
    item = await make_resource(client, h)
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):  # hidden requires a reason
            await db.execute(
                text("UPDATE content_items SET status='hidden' WHERE id=:i"),
                {"i": item["id"]},
            )
            await db.commit()
    async with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            await db.execute(
                text(
                    "INSERT INTO votes (user_id, item_id, value) SELECT author_id, id, 2 FROM content_items WHERE id=:i"
                ),
                {"i": item["id"]},
            )
            await db.commit()


async def test_patch_replaces_links_and_tags(client):
    _, h = await make_user(role="verified_ufazian")
    item = await make_resource(
        client, h, links=[{"url": "https://example.org/keep", "label": "old"}]
    )
    r = await client.patch(
        f"/api/resources/{item['id']}",
        json={
            "links": [
                {"url": "https://www.example.org/keep/", "label": "renamed"},
                {"url": "https://example.org/new"},
            ],
            "tags": ["calculus"],
            "difficulty": "advanced",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert [(link["label"]) for link in body["links"]] == ["renamed", ""]
    assert body["tags"] == ["calculus"] and body["difficulty"] == "advanced"
    bad = await client.patch(
        f"/api/resources/{item['id']}", json={"title": None}, headers=h
    )
    assert bad.status_code == 400


async def test_pending_items_are_private_until_published(client):
    _, plain = await make_user(role="user")
    _, admin = await make_user(role="admin")
    word = uniq()
    item = await make_resource(client, plain, title=f"Pending {word} notes")
    assert item["status"] == "pending_review"
    assert (
        await client.get(f"/api/resources/{item['call_number']}")
    ).status_code == 404
    assert (
        await client.get(f"/api/resources/{item['call_number']}", headers=plain)
    ).status_code == 200
    assert (await client.get("/api/search", params={"q": word})).json()["items"] == []
    await client.post(f"/api/content/{item['id']}/publish", headers=admin)
    assert (
        len((await client.get("/api/search", params={"q": word})).json()["items"]) == 1
    )


# --- listing ---------------------------------------------------------------------------------------
async def test_list_filters_and_cursor_pagination(client):
    _, h = await make_user(role="verified_ufazian")
    tag = uniq()
    made = [
        await make_resource(
            client,
            h,
            tags=[tag],
            difficulty="beginner" if i % 2 else "advanced",
            is_research=i == 0,
        )
        for i in range(5)
    ]
    seen, cursor = [], None
    for _ in range(5):
        r = await client.get(
            "/api/resources",
            params={"tag": tag, "limit": 2, **({"cursor": cursor} if cursor else {})},
        )
        page = r.json()
        seen += [i["id"] for i in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert seen == [m["id"] for m in reversed(made)]  # newest first, no gaps or repeats
    only = (
        await client.get(
            "/api/resources", params={"tag": tag, "difficulty": "beginner"}
        )
    ).json()
    assert len(only["items"]) == 2
    res = (
        await client.get("/api/resources", params={"tag": tag, "research": True})
    ).json()
    assert [i["id"] for i in res["items"]] == [made[0]["id"]]
    assert (await client.get("/api/resources", params={"cursor": "garbage"})).json()[
        "code"
    ] == "invalid_cursor"
    assert (
        await client.get("/api/resources", params={"limit": 500})
    ).status_code == 422


async def test_top_sort_orders_by_votes_and_pages(client):
    _, h = await make_user(role="verified_ufazian")
    tag = uniq()
    items = [await make_resource(client, h, tags=[tag]) for _ in range(3)]
    for item, voters in zip(items, (1, 3, 2)):
        for _ in range(voters):
            _, vh = await make_user()
            await client.put(
                f"/api/content/{item['id']}/vote", json={"value": 1}, headers=vh
            )
    ids, cursor = [], None
    while True:
        page = (
            await client.get(
                "/api/resources",
                params={
                    "tag": tag,
                    "sort": "top",
                    "limit": 2,
                    **({"cursor": cursor} if cursor else {}),
                },
            )
        ).json()
        ids += [(i["id"], i["vote_score"]) for i in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert [s for _, s in ids] == [3, 2, 1] and ids[0][0] == items[1]["id"]


async def test_tags_endpoint_counts_published_usage(client):
    _, h = await make_user(role="verified_ufazian")
    tag = uniq()
    await make_resource(client, h, tags=[tag])
    await make_resource(client, h, tags=[tag])
    r = (await client.get("/api/tags", params={"q": tag[:6], "limit": 50})).json()
    assert {"name": tag, "slug": tag, "count": 2} in r["items"]


# --- votes ---------------------------------------------------------------------------------------------
async def vote(client, item, headers, value):
    return await client.put(
        f"/api/content/{item['id']}/vote", json={"value": value}, headers=headers
    )


async def test_vote_flip_remove_and_viewer_state(client):
    _, owner = await make_user(role="verified_ufazian")
    _, h = await make_user()
    item = await make_resource(client, owner)
    assert (await vote(client, item, h, 1)).json() == {"vote_score": 1, "my_vote": 1}
    assert (await vote(client, item, h, 1)).json()["vote_score"] == 1  # idempotent
    assert (await vote(client, item, h, -1)).json() == {"vote_score": -1, "my_vote": -1}
    mine = (await client.get(f"/api/resources/{item['call_number']}", headers=h)).json()
    assert mine["my_vote"] == -1 and mine["vote_score"] == -1
    assert (await client.get(f"/api/resources/{item['call_number']}")).json()[
        "my_vote"
    ] == 0
    assert (await vote(client, item, h, 0)).json() == {"vote_score": 0, "my_vote": 0}
    assert (await vote(client, item, h, 0)).json()["vote_score"] == 0
    assert (await vote(client, item, h, 2)).status_code == 422


async def test_no_self_votes_and_hidden_items_are_404(client):
    _, owner = await make_user(role="verified_ufazian")
    item = await make_resource(client, owner)
    r = await vote(client, item, owner, 1)
    assert r.status_code == 403 and r.json()["code"] == "self_vote"
    _, admin = await make_user(role="admin")
    await client.post(
        f"/api/content/{item['id']}/hide", json={"reason": "off topic"}, headers=admin
    )
    _, h = await make_user()
    assert (await vote(client, item, h, 1)).status_code == 404
    assert (
        await client.put(
            f"/api/content/{uuid.uuid4()}/vote", json={"value": 1}, headers=h
        )
    ).status_code == 404


async def test_daily_vote_cap(client, monkeypatch):
    monkeypatch.setattr(settings, "VOTE_DAILY_CAP", 2)
    _, owner = await make_user(role="verified_ufazian")
    _, h = await make_user()
    items = [await make_resource(client, owner) for _ in range(3)]
    assert (await vote(client, items[0], h, 1)).status_code == 200
    assert (await vote(client, items[1], h, 1)).status_code == 200
    r = await vote(client, items[2], h, 1)
    assert r.status_code == 429 and r.json()["code"] == "vote_cap_reached"
    assert "retry-after" in r.headers
    assert (
        await vote(client, items[0], h, 0)
    ).status_code == 200  # taking a vote back is always allowed


async def test_concurrent_votes_keep_counter_exact(client):
    _, owner = await make_user(role="verified_ufazian")
    item = await make_resource(client, owner)
    voters = [await make_user() for _ in range(15)]
    rs = await asyncio.gather(*(vote(client, item, h, 1) for _, h in voters))
    assert all(r.status_code == 200 for r in rs)
    # the same user hammering the endpoint (double click, retries) still counts once
    _, dbl = await make_user()
    rs = await asyncio.gather(*(vote(client, item, dbl, 1) for _ in range(8)))
    assert all(r.status_code == 200 for r in rs)
    async with SessionLocal() as db:
        score = await db.scalar(
            select(ContentItem.vote_score).where(
                ContentItem.id == uuid.UUID(item["id"])
            )
        )
        rows = await db.scalar(
            select(func.count())
            .select_from(Vote)
            .where(Vote.item_id == uuid.UUID(item["id"]))
        )
    assert score == rows == 16


async def test_concurrent_flips_never_drift(client):
    _, owner = await make_user(role="verified_ufazian")
    item = await make_resource(client, owner)
    users = [await make_user() for _ in range(6)]
    await asyncio.gather(
        *(vote(client, item, h, v) for _, h in users for v in (1, -1, 1, 0, -1))
    )
    async with SessionLocal() as db:
        score = await db.scalar(
            select(ContentItem.vote_score).where(
                ContentItem.id == uuid.UUID(item["id"])
            )
        )
        total = await db.scalar(
            select(func.coalesce(func.sum(Vote.value), 0)).where(
                Vote.item_id == uuid.UUID(item["id"])
            )
        )
    assert score == total


# --- bookmarks --------------------------------------------------------------------------------------------
async def test_bookmarks_are_idempotent_and_counted_once(client):
    _, owner = await make_user(role="verified_ufazian")
    item = await make_resource(client, owner)
    _, h = await make_user()
    url = f"/api/content/{item['id']}/bookmark"
    rs = await asyncio.gather(*(client.put(url, headers=h) for _ in range(6)))
    assert {r.json()["bookmark_count"] for r in rs} <= {1}
    mine = (await client.get(f"/api/resources/{item['call_number']}", headers=h)).json()
    assert mine["bookmarked"] is True and mine["bookmark_count"] == 1
    assert (await client.delete(url, headers=h)).json() == {
        "bookmark_count": 0,
        "bookmarked": False,
    }
    assert (await client.delete(url, headers=h)).json()["bookmark_count"] == 0
    async with SessionLocal() as db:
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Bookmark)
                .where(Bookmark.item_id == uuid.UUID(item["id"]))
            )
            == 0
        )


# --- duplicates ------------------------------------------------------------------------------------------------
async def test_duplicate_detection_by_link_and_title(client):
    _, h = await make_user(role="verified_ufazian")
    word = uniq()
    item = await make_resource(
        client,
        h,
        title=f"Introduction to {word} Algorithms",
        links=[{"url": f"https://example.org/{word}/guide"}],
    )
    same = await client.get(
        "/api/resources/duplicates",
        params={"url": f"http://www.example.org/{word}/guide/?utm_campaign=x#top"},
    )
    assert [(d["call_number"], d["match"]) for d in same.json()] == [
        (item["call_number"], "same_link")
    ]
    similar = await client.get(
        "/api/resources/duplicates",
        params={"title": f"Introduction to {word} Algorithm"},
    )
    assert [(d["call_number"], d["match"]) for d in similar.json()] == [
        (item["call_number"], "similar_title")
    ]
    assert (
        await client.get(
            "/api/resources/duplicates", params={"title": "Cooking with fire " + word}
        )
    ).json() == []
    assert (
        await client.get("/api/resources/duplicates", params={"url": "ftp://x"})
    ).status_code == 400


# --- rate limits ------------------------------------------------------------------------------------------------
async def test_write_and_search_endpoints_are_rate_limited(client):
    _, h = await make_user(role="verified_ufazian")
    codes = [
        (await client.post("/api/resources", json={}, headers=h)).status_code
        for _ in range(31)
    ]
    assert codes[-1] == 429 and codes[0] == 422
    codes = [
        (await client.get("/api/search", params={"q": "algebra"})).status_code
        for _ in range(31)
    ]
    assert codes[-1] == 429
