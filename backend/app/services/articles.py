"""Articles: Markdown stored as written and as sanitized HTML (nh3), with slug, excerpt, reading time."""

import math
import uuid
from datetime import datetime, UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.content import Article, ContentStatus, ContentType, Tag
from app.models.user import Role, User
from app.api.permissions import can_manage, initial_status
from app.schemas.articles import (
    ArticleCard,
    ArticleIn,
    ArticleOut,
    ArticlePatch,
    PreviewOut,
)
from app.schemas.common import Page
from app.services import audit, markdown
from app.services import content as base
from app.services.uploads import owned_attachment

WORDS_PER_MINUTE = 200


def derive(md: str, excerpt: str = "") -> dict:
    """Everything computed from the Markdown: html, toc, reading time, excerpt."""
    text = markdown.plain_text(md)
    if not text:
        raise AppError(
            "The article has no text.", fields={"body_md": "Write something."}
        )
    if not excerpt:
        excerpt = text if len(text) <= 200 else text[:200].rsplit(" ", 1)[0] + "…"
    return {
        "body_html": markdown.render(md),
        "toc": markdown.headings(md),
        "reading_minutes": max(1, math.ceil(len(text.split()) / WORDS_PER_MINUTE)),
        "description": excerpt,
    }


def preview(md: str) -> PreviewOut:
    d = derive(md)
    return PreviewOut(
        body_html=d["body_html"], toc=d["toc"], reading_minutes=d["reading_minutes"]
    )


async def _unique_slug(db: AsyncSession, title: str, call_number: str) -> str:
    base_slug = base.slugify(title) or "article"
    taken = await db.scalar(select(Article.id).where(Article.slug == base_slug))
    return base_slug if taken is None else f"{base_slug}-{call_number.lower()}"


async def create(db: AsyncSession, user: User, data: ArticleIn) -> Article:
    if data.cover_attachment_id:
        await owned_attachment(db, user, data.cover_attachment_id, "image")
    status = initial_status(user) if data.publish else ContentStatus.draft.value
    call_number = await base._call_number(db, ContentType.article)
    item = Article(
        id=uuid.uuid4(),
        author_id=user.id,
        author=user,
        status=status,
        call_number=call_number,
        slug=await _unique_slug(db, data.title, call_number),
        title=data.title,
        body_md=data.body_md,
        cover_attachment_id=data.cover_attachment_id,
        is_research=data.is_research,
        published_at=datetime.now(UTC) if status == "published" else None,
        tags=await base._tags(db, data.tags),
        **derive(data.body_md, data.excerpt),
    )
    db.add(item)
    await db.flush()
    return await base.load_item(db, Article, id=item.id)  # type: ignore[return-value]


async def update(
    db: AsyncSession, actor: User, item: Article, data: ArticlePatch
) -> Article:
    changes = data.model_dump(exclude_unset=True, exclude={"tags", "publish"})
    for k in ("title", "body_md", "is_research"):
        if k in changes and changes[k] is None:
            raise AppError(f"{k} cannot be empty", fields={k: "Required"})
    if changes.get("cover_attachment_id"):
        await owned_attachment(db, actor, changes["cover_attachment_id"], "image")
    before = {k: getattr(item, k) for k in changes}
    if "body_md" in changes or "excerpt" in changes:
        # Without a new excerpt, keep the old one unless the body changed under an auto excerpt.
        derived = derive(
            changes.get("body_md", item.body_md),
            changes.get("excerpt") or "",
        )
        for k, v in derived.items():
            setattr(item, k, v)
    changes.pop("excerpt", None)
    for k, v in changes.items():
        setattr(item, k, v)
    if data.tags is not None:
        item.tags = await base._tags(db, data.tags)
    if data.publish is not None:
        _set_published(item, actor, data.publish)
    item.updated_at = func.now()  # type: ignore[assignment]
    if actor.id != item.author_id:
        await audit.record(
            db,
            actor_id=actor.id,
            action="content.edit",
            target_type="content_item",
            target_id=item.id,
            before={k: v for k, v in before.items() if k != "body_md"},
            after={k: v for k, v in changes.items() if k != "body_md"},
        )
    await db.flush()
    return await base.load_item(db, Article, id=item.id)  # type: ignore[return-value]


def _set_published(item: Article, actor: User, publish: bool) -> None:
    if item.status == ContentStatus.hidden:
        return  # only moderation un-hides
    if publish and item.status == ContentStatus.draft:
        # The author's trust decides; an admin editing someone else's draft cannot publish it for them.
        trusted = item.author.role in (Role.verified_ufazian, Role.admin)
        item.status = (
            ContentStatus.published if trusted else ContentStatus.pending_review
        ).value
        if item.status == ContentStatus.published and item.published_at is None:
            item.published_at = datetime.now(UTC)
    elif not publish and item.status != ContentStatus.draft:
        item.status = ContentStatus.draft.value


async def present(
    db: AsyncSession, viewer: User | None, items: list[Article], full: bool = False
) -> list[ArticleCard]:
    votes, marks = await base.viewer_state(db, viewer, [i.id for i in items])
    out = []
    for i in items:
        o = (ArticleOut if full else ArticleCard).model_validate(
            i, from_attributes=True
        )
        if isinstance(o, ArticleOut) and not (viewer and can_manage(viewer, i)):
            o.body_md = None
        out.append(base.decorate(o, i, viewer, votes, marks))
    return out


async def find(db: AsyncSession, ref: str) -> Article | None:
    """By call number (ART-0087) or slug."""
    where = {"call_number": ref.upper()} if ref[:4].upper() == "ART-" else {"slug": ref}
    return await base.load_item(db, Article, **where)


async def list_articles(
    db: AsyncSession,
    viewer: User | None,
    *,
    sort: str,
    tag: str | None,
    research: bool | None,
    mine: User | None,
    cursor: str | None,
    limit: int,
) -> Page[ArticleCard]:
    stmt = select(Article)
    if mine is not None:
        stmt = stmt.where(Article.author_id == mine.id)
    else:
        stmt = stmt.where(Article.status == ContentStatus.published.value)
    if tag:
        stmt = stmt.where(Article.tags.any(Tag.slug == tag))
    if research is not None:
        stmt = stmt.where(Article.is_research.is_(research))
    rows, nxt = await base.keyset_page(db, stmt, Article, sort, cursor, limit)
    return Page(items=await present(db, viewer, rows), next_cursor=nxt)
