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
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
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
    # Slice 4 (uploads) turns this into a foreign key to the attachments table.
    primary_attachment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

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
