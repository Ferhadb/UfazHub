import pytest

from tests.factories import (
    article_payload,
    make_article,
    make_user,
    png_bytes,
)


async def test_publish_slug_reading_time_excerpt_and_sanitised_html(client):
    _, h = await make_user("verified_ufazian")
    body = (
        "## Start early\n\n"
        + "word " * 450
        + "\n\n<script>alert(1)</script> [x](https://example.org)"
    )
    a = await make_article(client, h, body_md=body, title="Ça marche: l'été à Bakı")
    assert a["status"] == "published" and a["call_number"].startswith("ART-")
    assert a["slug"].startswith("ça-marche")
    assert a["reading_minutes"] == 3
    assert a["excerpt"].startswith("Start early word")
    assert "<script" not in a["body_html"]
    assert 'rel="noopener nofollow ugc"' in a["body_html"]
    assert a["toc"] == [{"level": 2, "text": "Start early"}]
    assert a["body_md"] == body  # the author gets the source back for editing


async def test_slug_collision_gets_call_number_suffix(client):
    _, h = await make_user("verified_ufazian")
    a = await make_article(client, h, title="Same title")
    b = await make_article(client, h, title="Same title")
    assert (
        a["slug"] == "same-title"
        and b["slug"] == f"same-title-{b['call_number'].lower()}"
    )


async def test_get_by_slug_and_by_call_number_hides_source_from_others(client):
    _, h = await make_user("verified_ufazian")
    a = await make_article(client, h)
    for ref in (a["slug"], a["call_number"], a["call_number"].lower()):
        r = await client.get(f"/api/articles/{ref}")
        assert r.status_code == 200 and r.json()["id"] == a["id"]
        assert r.json()["body_md"] is None
    assert (await client.get("/api/articles/nope")).status_code == 404


async def test_drafts_are_private_to_author_and_admin(client):
    _, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    d = await make_article(client, h, publish=False)
    assert d["status"] == "draft"
    ref = d["slug"]
    assert (await client.get(f"/api/articles/{ref}")).status_code == 404
    assert (await client.get(f"/api/articles/{ref}", headers=other)).status_code == 404
    assert (await client.get(f"/api/articles/{ref}", headers=h)).status_code == 200
    assert (await client.get(f"/api/articles/{ref}", headers=admin)).status_code == 200
    listed = (await client.get("/api/articles")).json()["items"]
    assert d["id"] not in [i["id"] for i in listed]
    mine = (await client.get("/api/me/articles", headers=h)).json()["items"]
    assert d["id"] in [i["id"] for i in mine]
    assert (await client.get("/api/me/articles")).status_code == 401


async def test_non_students_wait_for_review(client):
    _, h = await make_user("user")
    a = await make_article(client, h)
    assert a["status"] == "pending_review"
    assert (await client.get(f"/api/articles/{a['slug']}")).status_code == 404


async def test_publish_toggle(client):
    _, h = await make_user("verified_ufazian")
    d = await make_article(client, h, publish=False)
    r = await client.patch(
        f"/api/articles/{d['id']}", json={"publish": True}, headers=h
    )
    assert r.json()["status"] == "published" and r.json()["published_at"]
    r = await client.patch(
        f"/api/articles/{d['id']}", json={"publish": False}, headers=h
    )
    assert r.json()["status"] == "draft"


async def test_edit_recomputes_derived_fields_and_keeps_slug(client):
    _, h = await make_user("verified_ufazian")
    a = await make_article(client, h)
    r = await client.patch(
        f"/api/articles/{a['id']}",
        json={"title": "New title", "body_md": "### Only this\n\n" + "text " * 30},
        headers=h,
    )
    j = r.json()
    assert j["slug"] == a["slug"] and j["title"] == "New title"
    assert j["toc"] == [{"level": 3, "text": "Only this"}]
    assert (
        await client.patch(f"/api/articles/{a['id']}", json={"title": None}, headers=h)
    ).status_code == 400


async def test_admin_edit_is_audited_and_strangers_are_refused(client):
    from sqlalchemy import select

    from app.db.session import SessionLocal
    from app.models.audit import AuditLog

    _, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    a = await make_article(client, h)
    assert (
        await client.patch(
            f"/api/articles/{a['id']}", json={"title": "Hijack"}, headers=other
        )
    ).status_code == 403
    assert (
        await client.patch(
            f"/api/articles/{a['id']}", json={"title": "Fixed typo"}, headers=admin
        )
    ).status_code == 200
    async with SessionLocal() as db:
        row = (
            await db.execute(select(AuditLog).where(AuditLog.target_id == a["id"]))
        ).scalar_one()
    assert row.action == "content.edit" and row.after == {"title": "Fixed typo"}


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
    kw = {
        "guest": None,
        "unverified": dict(verified=False),
        "muted": dict(status="muted"),
        "banned": dict(status="banned"),
        "user": {},
    }[actor]
    headers = (await make_user(**kw))[1] if kw is not None else {}
    r = await client.post("/api/articles", json=article_payload(), headers=headers)
    assert r.status_code == status


async def test_validation(client):
    _, h = await make_user("verified_ufazian")
    r = await client.post(
        "/api/articles", json=article_payload(body_md="short"), headers=h
    )
    assert r.status_code == 422 and "body_md" in r.json()["fields"]
    r = await client.post(
        "/api/articles", json=article_payload(body_md="x" * 60_001), headers=h
    )
    assert r.status_code == 422


async def test_cover_must_be_your_own_image(client):
    _, h = await make_user("verified_ufazian")
    _, other = await make_user("verified_ufazian")
    up = await client.post(
        "/api/uploads",
        files={"file": ("c.png", png_bytes(), "image/png")},
        data={"purpose": "cover"},
        headers=h,
    )
    cover = up.json()["id"]
    a = await make_article(client, h, cover_attachment_id=cover)
    assert set(a["cover"]["urls"]) == {"sm", "md", "lg"}
    r = await client.post(
        "/api/articles", json=article_payload(cover_attachment_id=cover), headers=other
    )
    assert r.status_code == 422 and r.json()["code"] == "invalid_attachment"
    pdf = await client.post(
        "/api/uploads",
        files={"file": ("a.pdf", b"%PDF-1.4 x", "application/pdf")},
        headers=h,
    )
    r = await client.post(
        "/api/articles",
        json=article_payload(cover_attachment_id=pdf.json()["id"]),
        headers=h,
    )
    assert r.status_code == 422


async def test_list_filters_sorts_and_cursor(client):
    _, h = await make_user("verified_ufazian")
    made = [
        await make_article(
            client, h, title=f"Article number {i}", tags=["pagetest", "t" + str(i % 2)]
        )
        for i in range(5)
    ]
    page = (await client.get("/api/articles?limit=2&tag=pagetest")).json()
    assert [i["id"] for i in page["items"]] == [made[4]["id"], made[3]["id"]]
    seen = [i["id"] for i in page["items"]]
    nxt = page["next_cursor"]
    while nxt:
        page = (
            await client.get(f"/api/articles?limit=2&tag=pagetest&cursor={nxt}")
        ).json()
        seen += [i["id"] for i in page["items"]]
        nxt = page["next_cursor"]
    assert seen == [m["id"] for m in reversed(made)]
    tagged = (await client.get("/api/articles?tag=pagetest&tag=t1")).json()["items"]
    assert 2 <= len(tagged) <= 3
    assert (await client.get("/api/articles?cursor=garbage")).status_code == 400


async def test_preview_endpoint_uses_the_same_sanitiser(client):
    _, h = await make_user("user")
    r = await client.post(
        "/api/articles/preview",
        json={"body_md": "## Hi\n\n<img src=x onerror=alert(1)>"},
        headers=h,
    )
    assert r.status_code == 200
    j = r.json()
    assert "<img" not in j["body_html"] and j["toc"] == [{"level": 2, "text": "Hi"}]
    assert (
        await client.post("/api/articles/preview", json={"body_md": "x"})
    ).status_code == 401


async def test_body_is_searchable_and_drafts_are_not(client):
    _, h = await make_user("verified_ufazian")
    await make_article(
        client,
        h,
        title="Plain title",
        body_md="## Notes\n\n" + "The zygomorphic petals unfurl. " * 3,
    )
    await make_article(
        client,
        h,
        title="Secret",
        body_md="## Notes\n\n" + "The quixotic hidden draft text. " * 3,
        publish=False,
    )
    r = (await client.get("/api/search?q=zygomorphic")).json()["items"]
    assert [i["title"] for i in r] == ["Plain title"] and r[0]["type"] == "article"
    assert (await client.get("/api/search?q=quixotic")).json()["items"] == []


async def test_vote_and_bookmark_work_on_articles(client):
    _, h = await make_user("verified_ufazian")
    _, reader = await make_user("user")
    a = await make_article(client, h)
    v = await client.put(
        f"/api/content/{a['id']}/vote", json={"value": 1}, headers=reader
    )
    assert v.json()["vote_score"] == 1
    await client.put(f"/api/content/{a['id']}/bookmark", headers=reader)
    got = (await client.get(f"/api/articles/{a['slug']}", headers=reader)).json()
    assert got["my_vote"] == 1 and got["bookmarked"] and got["bookmark_count"] == 1
