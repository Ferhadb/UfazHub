"""Reports filed by readers and appeals filed by authors / banned users."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.user import User, _in, _now


class ReportReason(enum.StrEnum):
    spam = "spam"
    offensive = "offensive"
    copyright = "copyright"
    inaccurate = "inaccurate"
    broken_link = "broken_link"
    off_topic = "off_topic"
    other = "other"


class ReportStatus(enum.StrEnum):
    open = "open"
    actioned = "actioned"  # the item was hidden
    dismissed = "dismissed"


class AppealKind(enum.StrEnum):
    content = "content"
    ban = "ban"


class AppealStatus(enum.StrEnum):
    open = "open"
    accepted = "accepted"
    rejected = "rejected"


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("item_id", "reporter_id"),
        CheckConstraint(_in("reason", ReportReason), name="reason"),
        CheckConstraint(_in("status", ReportStatus), name="status"),
        Index("ix_reports_item_status", "item_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE")
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    reason: Mapped[str] = mapped_column(String(16))
    note: Mapped[str] = mapped_column(Text, server_default="")
    status: Mapped[str] = mapped_column(
        String(10), server_default=ReportStatus.open.value
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()

    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id], lazy="joined")


class Appeal(Base):
    """`item_id` is set for a content appeal and null for a ban appeal."""

    __tablename__ = "appeals"
    __table_args__ = (
        CheckConstraint(_in("kind", AppealKind), name="kind"),
        CheckConstraint(_in("status", AppealStatus), name="status"),
        CheckConstraint(
            "(kind = 'content') = (item_id IS NOT NULL)", name="item_matches_kind"
        ),
        # One open appeal per user and subject; a rejected one may be followed by a new one.
        Index(
            "uq_appeals_open_item",
            "user_id",
            "item_id",
            unique=True,
            postgresql_where="status = 'open' AND item_id IS NOT NULL",
        ),
        Index(
            "uq_appeals_open_ban",
            "user_id",
            unique=True,
            postgresql_where="status = 'open' AND item_id IS NULL",
        ),
        Index("ix_appeals_status_created", "status", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(8))
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE")
    )
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(10), server_default=AppealStatus.open.value
    )
    response: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")
