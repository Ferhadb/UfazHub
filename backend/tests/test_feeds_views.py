import uuid
from datetime import UTC, datetime, timedelta
from xml.etree import ElementTree as ET

from sqlalchemy import select, update

from app.db.session import SessionLocal
from app.models.content import ContentItem, ContentView
from app.services.views import VIEW_WINDOW, cleanup_retention
from tests.factories import make_article, make_resource, make_user


async def test_rss_and_atom_expose_only_published_articles_in_tag(client):
    _, author = await make_user("verified_ufazian")
    _, admin = await make_user("admin")
    tag = "feed-" + uuid.uuid4().hex[:8]
    good = await make_article(client, author, title="A & B", tags=[tag])
    other = await make_article(client, author, tags=["elsewhere"])
    draft = await make_article(client, author, tags=[tag], publish=False)
    hidden = await make_article(client, author, tags=[tag])
    await client.post(
        f"/api/content/{hidden['id']}/hide", json={"reason": "review"}, headers=admin
    )

    rss = await client.get(f"/api/feeds/tags/{tag}.rss")
    assert (
        rss.status_code == 200 and "application/rss+xml" in rss.headers["content-type"]
    )
    xml = ET.fromstring(rss.content)
    entries = xml.findall("./channel/item")
    assert [entry.findtext("title") for entry in entries] == ["A & B"]
    assert entries[0].findtext("link").endswith(f"/articles/{good['slug']}")
    assert entries[0].findtext("pubDate")
    assert all(x["id"] not in rss.text for x in (other, draft, hidden))

    atom = await client.get(f"/api/feeds/tags/{tag}.atom")
    assert (
        atom.status_code == 200
        and "application/atom+xml" in atom.headers["content-type"]
    )
    ns = {"a": "http://www.w3.org/2005/Atom"}
    entries = ET.fromstring(atom.content).findall("a:entry", ns)
    assert (
        len(entries) == 1 and entries[0].findtext("a:title", namespaces=ns) == "A & B"
    )
    assert entries[0].findtext("a:published", namespaces=ns)
    assert (await client.get("/api/feeds/articles.rss")).status_code == 200
    assert (await client.get("/api/feeds/articles.atom")).status_code == 200
    assert (await client.get("/api/feeds/tags/unknown-tag.atom")).status_code == 404


async def test_view_count_deduplicates_without_ip_and_recounts_after_window(client):
    _, author = await make_user("verified_ufazian")
    article = await make_article(client, author)
    item_id = article["id"]
    first = await client.post(f"/api/content/{item_id}/view")
    assert first.json() == {"view_count": 1}
    assert "httponly" in first.headers["set-cookie"].lower()
    assert (await client.post(f"/api/content/{item_id}/view")).json() == {
        "view_count": 1
    }
    async with SessionLocal() as db:
        rows = (
            await db.scalars(
                select(ContentView).where(ContentView.item_id == uuid.UUID(item_id))
            )
        ).all()
        assert len(rows) == 1 and len(rows[0].visitor_hash) == 64
        assert "127.0.0.1" not in rows[0].visitor_hash
        await db.execute(
            update(ContentView)
            .where(ContentView.item_id == uuid.UUID(item_id))
            .values(viewed_at=datetime.now(UTC) - VIEW_WINDOW - timedelta(seconds=1))
        )
        await db.commit()
    assert (await client.post(f"/api/content/{item_id}/view")).json() == {
        "view_count": 2
    }
    client.cookies.clear()
    assert (await client.post(f"/api/content/{item_id}/view")).json() == {
        "view_count": 3
    }


async def test_view_rejects_drafts_and_missing_items_and_retention_removes_receipts(
    client,
):
    _, author = await make_user("verified_ufazian")
    draft = await make_article(client, author, publish=False)
    assert (await client.post(f"/api/content/{draft['id']}/view")).status_code == 404
    assert (await client.post(f"/api/content/{uuid.uuid4()}/view")).status_code == 404
    article = await make_article(client, author)
    resource = await make_resource(client, author)
    for item in (article, resource):
        assert (await client.post(f"/api/content/{item['id']}/view")).json()[
            "view_count"
        ] == 1
    async with SessionLocal() as db:
        await db.execute(
            update(ContentView)
            .where(ContentView.item_id == uuid.UUID(article["id"]))
            .values(viewed_at=datetime.now(UTC) - VIEW_WINDOW - timedelta(seconds=1))
        )
        await db.commit()
    async with SessionLocal() as db:
        assert await cleanup_retention(db) >= 1
    async with SessionLocal() as db:
        assert (
            await db.scalar(
                select(ContentView).where(
                    ContentView.item_id == uuid.UUID(article["id"])
                )
            )
            is None
        )
        assert (
            await db.scalar(
                select(ContentItem.view_count).where(
                    ContentItem.id == uuid.UUID(article["id"])
                )
            )
            == 1
        )
