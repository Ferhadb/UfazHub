"""Public RSS and Atom article feeds; only published content is exposed."""

from datetime import UTC, datetime
from email.utils import format_datetime
from urllib.parse import quote
from xml.etree import ElementTree as ET

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFound
from app.models.content import Article, ContentStatus, Tag

ATOM = "http://www.w3.org/2005/Atom"
LIMIT = 50
ET.register_namespace("", ATOM)


def _url(path: str) -> str:
    return settings.SITE_URL.rstrip("/") + path


def _when(value: datetime | None, fallback: datetime) -> datetime:
    result = value or fallback
    return result if result.tzinfo else result.replace(tzinfo=UTC)


async def articles_for_feed(
    db: AsyncSession, tag: str | None
) -> tuple[list[Article], str]:
    title = "UFAZ Hub articles"
    stmt = select(Article).where(Article.status == ContentStatus.published.value)
    if tag is not None:
        found = await db.scalar(select(Tag).where(Tag.slug == tag))
        if found is None:
            raise NotFound("Tag not found.")
        title += f" · {found.name}"
        stmt = stmt.where(Article.tags.any(Tag.id == found.id))
    rows = await db.scalars(
        stmt.order_by(Article.published_at.desc().nullslast(), Article.id.desc()).limit(
            LIMIT
        )
    )
    return list(rows.all()), title


def render_feed(items: list[Article], title: str, tag: str | None, kind: str) -> bytes:
    suffix = "rss" if kind == "rss" else "atom"
    path = (
        f"/api/feeds/tags/{quote(tag, safe='')}.{suffix}"
        if tag
        else f"/api/feeds/articles.{suffix}"
    )
    home = _url("/articles")
    self_url = _url(path)

    if kind == "rss":
        root = ET.Element("rss", version="2.0")
        channel = ET.SubElement(root, "channel")
        for key, value in (
            ("title", title),
            ("link", home),
            ("description", "Articles from UFAZ Hub"),
        ):
            ET.SubElement(channel, key).text = value
        for article in items:
            item = ET.SubElement(channel, "item")
            link = _url(f"/articles/{quote(article.slug, safe='')}")
            for key, value in (
                ("title", article.title),
                ("link", link),
                ("guid", link),
                ("description", article.description),
                (
                    "pubDate",
                    format_datetime(_when(article.published_at, article.created_at)),
                ),
            ):
                ET.SubElement(item, key).text = value
    else:
        root = ET.Element(f"{{{ATOM}}}feed")
        ET.SubElement(root, f"{{{ATOM}}}title").text = title
        ET.SubElement(root, f"{{{ATOM}}}id").text = self_url
        ET.SubElement(root, f"{{{ATOM}}}link", href=self_url, rel="self")
        ET.SubElement(root, f"{{{ATOM}}}link", href=home)
        latest = max(
            (_when(i.updated_at, i.created_at) for i in items),
            default=datetime.now(UTC),
        )
        ET.SubElement(root, f"{{{ATOM}}}updated").text = latest.isoformat()
        for article in items:
            entry = ET.SubElement(root, f"{{{ATOM}}}entry")
            link = _url(f"/articles/{quote(article.slug, safe='')}")
            ET.SubElement(entry, f"{{{ATOM}}}title").text = article.title
            ET.SubElement(entry, f"{{{ATOM}}}id").text = link
            ET.SubElement(entry, f"{{{ATOM}}}link", href=link)
            ET.SubElement(entry, f"{{{ATOM}}}summary").text = article.description
            ET.SubElement(entry, f"{{{ATOM}}}published").text = _when(
                article.published_at, article.created_at
            ).isoformat()
            ET.SubElement(entry, f"{{{ATOM}}}updated").text = _when(
                article.updated_at, article.created_at
            ).isoformat()
            author = ET.SubElement(entry, f"{{{ATOM}}}author")
            ET.SubElement(author, f"{{{ATOM}}}name").text = article.author.display_name

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
