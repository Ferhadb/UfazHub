"""Content base table (joined-table inheritance), tags, votes, bookmarks.

Every content type is a row in `content_items` plus a subtype row sharing its id, so votes,
bookmarks, tags and search point at one table with real foreign keys.
`search_vector` is maintained by database triggers (see migration 0003).
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.media import Attachment
from app.models.user import User, _in, _now


class ContentType(enum.StrEnum):
    resource = "resource"
    article = "article"
    collection = "collection"
    question = "question"


CALL_PREFIX = {
    ContentType.resource: "RES",
    ContentType.article: "ART",
    ContentType.collection: "COL",
    ContentType.question: "QST",
}


class ContentStatus(enum.StrEnum):
    draft = "draft"
    pending_review = "pending_review"
    published = "published"
    hidden = "hidden"


class ResourceType(enum.StrEnum):
    book = "book"
    video = "video"
    course = "course"
    article = "article"
    paper = "paper"
    notes = "notes"
    exam = "exam"
    tool = "tool"
    dataset = "dataset"
    other = "other"


class Difficulty(enum.StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class ContentItem(Base):
    __tablename__ = "content_items"
    __table_args__ = (
        CheckConstraint(_in("type", ContentType), name="type"),
        CheckConstraint(_in("status", ContentStatus), name="status"),
        CheckConstraint(
            "status <> 'hidden' OR hidden_reason IS NOT NULL", name="hidden_reason"
        ),
        Index(
            "ix_content_items_search_vector", "search_vector", postgresql_using="gin"
        ),
        # Created in migration 0003 (needs the f_unaccent wrapper); declared so `alembic check` stays clean.
        Index(
            "ix_content_items_title_trgm",
            text("f_unaccent(lower(title)) gin_trgm_ops"),
            postgresql_using="gin",
        ),
        Index("ix_content_items_feed", "status", "created_at", "id"),
        Index("ix_content_items_top", "status", "vote_score", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(12))
    call_number: Mapped[str] = mapped_column(String(16), unique=True)
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[str] = mapped_column(
        String(16), server_default=ContentStatus.pending_review.value
    )
    hidden_reason: Mapped[str | None] = mapped_column(Text)
    is_research: Mapped[bool] = mapped_column(Boolean, server_default="false")
    vote_score: Mapped[int] = mapped_column(Integer, server_default="0")
    bookmark_count: Mapped[int] = mapped_column(Integer, server_default="0")
    comment_count: Mapped[int] = mapped_column(Integer, server_default="0")
    view_count: Mapped[int] = mapped_column(BigInteger, server_default="0")
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, deferred=True)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    author: Mapped[User] = relationship(lazy="joined")
    tags: Mapped[list["Tag"]] = relationship(
        secondary="content_tags", order_by="Tag.slug", lazy="selectin"
    )

    __mapper_args__ = {"polymorphic_on": "type"}


class Resource(ContentItem):
    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(_in("resource_type", ResourceType), name="resource_type"),
        CheckConstraint(_in("difficulty", Difficulty), name="difficulty"),
        CheckConstraint(
            "time_commitment_minutes IS NULL OR time_commitment_minutes >= 0",
            name="time_commitment",
        ),
        Index("ix_resources_difficulty", "difficulty"),
    )
    __mapper_args__ = {"polymorphic_identity": ContentType.resource.value}

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    resource_type: Mapped[str] = mapped_column(String(12))
    category: Mapped[str] = mapped_column(String(60), server_default="")
    difficulty: Mapped[str] = mapped_column(String(14))
    time_commitment_minutes: Mapped[int | None] = mapped_column(Integer)
    prerequisites: Mapped[str] = mapped_column(Text, server_default="")
    best_part: Mapped[str] = mapped_column(Text, server_default="")
    warning: Mapped[str] = mapped_column(Text, server_default="")
    student_note: Mapped[str] = mapped_column(Text, server_default="")
    primary_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL")
    )
    attachment: Mapped[Attachment | None] = relationship(lazy="joined")

    links: Mapped[list["ResourceLink"]] = relationship(
        order_by="ResourceLink.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ResourceLink(Base):
    __tablename__ = "resource_links"
    __table_args__ = (
        UniqueConstraint("resource_id", "canonical_url"),
        Index("ix_resource_links_canonical_url", "canonical_url"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    resource_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("resources.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048))
    label: Mapped[str] = mapped_column(String(120), server_default="")
    position: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    # Filled by the `fetch_link_preview` job; `preview_fetched_at` is set even when the fetch failed.
    preview_title: Mapped[str | None] = mapped_column(String(200))
    preview_image: Mapped[str | None] = mapped_column(String(2048))
    preview_favicon: Mapped[str | None] = mapped_column(String(2048))
    preview_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(40))
    slug: Mapped[str] = mapped_column(String(48), unique=True)


class ContentTag(Base):
    __tablename__ = "content_tags"

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        CheckConstraint("value IN (-1, 1)", name="value"),
        Index("ix_votes_user_updated", "user_id", "updated_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = _now()


class Article(ContentItem):
    """`description` on the base row holds the excerpt, so search and cards need no special case."""

    __tablename__ = "articles"
    __table_args__ = (CheckConstraint("reading_minutes >= 1", name="reading_minutes"),)
    __mapper_args__ = {"polymorphic_identity": ContentType.article.value}

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    body_md: Mapped[str] = mapped_column(Text)
    body_html: Mapped[str] = mapped_column(Text)  # sanitized at write time (nh3)
    toc: Mapped[list] = mapped_column(JSONB, server_default="[]")  # [{level, text}]
    reading_minutes: Mapped[int] = mapped_column(SmallInteger, server_default="1")
    cover_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL")
    )
    cover: Mapped[Attachment | None] = relationship(lazy="joined")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def excerpt(self) -> str:
        return self.description


class Collection(ContentItem):
    __tablename__ = "collections"
    __mapper_args__ = {"polymorphic_identity": ContentType.collection.value}

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    items: Mapped[list["CollectionItem"]] = relationship(
        order_by="CollectionItem.position",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class CollectionItem(Base):
    __tablename__ = "collection_items"
    __table_args__ = (UniqueConstraint("collection_id", "item_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"), index=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(SmallInteger)
    note: Mapped[str] = mapped_column(Text, server_default="")
    item: Mapped[ContentItem] = relationship(lazy="joined", innerjoin=True)


class Comment(Base):
    """Threaded one level: `parent_id` always points at a top-level comment."""

    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_item_created", "item_id", "created_at", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()

    author: Mapped[User] = relationship(lazy="joined")
