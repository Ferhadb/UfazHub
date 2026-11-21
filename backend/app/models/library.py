"""Course taxonomy, tag follows and reading lists."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import _now

LEVELS = ("L1", "L2", "L3", "M1", "M2")


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(48), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, server_default="")


class Course(Base):
    """A course page such as "Algorithms L2"; content attaches through `content_courses`."""

    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            f"level IN ({', '.join(repr(v) for v in LEVELS)})", name="level"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("programs.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    level: Mapped[str] = mapped_column(String(2))
    description: Mapped[str] = mapped_column(Text, server_default="")

    program: Mapped[Program] = relationship(lazy="joined")


class ContentCourse(Base):
    """`start_position` (1-based) puts the item on the course's ordered "start here" path."""

    __tablename__ = "content_courses"
    __table_args__ = (
        CheckConstraint("start_position IS NULL OR start_position >= 1", name="pos"),
    )

    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    start_position: Mapped[int | None] = mapped_column(SmallInteger)


class TagFollow(Base):
    __tablename__ = "tag_follows"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class ReadingList(Base):
    """Private unless `share_token` is set; the token is the whole capability to read it."""

    __tablename__ = "reading_lists"
    __table_args__ = (Index("ix_reading_lists_owner", "owner_id", "created_at", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(80))
    share_token: Mapped[str | None] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime] = _now()


class ReadingListItem(Base):
    __tablename__ = "reading_list_items"

    list_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reading_lists.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    added_at: Mapped[datetime] = _now()
