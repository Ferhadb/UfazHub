"""Questions and answers (content subtypes), the reputation ledger and notifications."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.content import ContentItem, ContentType
from app.models.user import _in, _now


class Question(ContentItem):
    """The body lives in `description`; `duplicate_of_id` makes the page redirect to the original."""

    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("duplicate_of_id <> id", name="not_own_duplicate"),
        Index("ix_questions_topic", "topic"),
    )
    __mapper_args__ = {"polymorphic_identity": ContentType.question.value}

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    topic: Mapped[str] = mapped_column(String(60))
    linked_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("resources.id", ondelete="SET NULL")
    )
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("questions.id", ondelete="SET NULL"), index=True
    )

    @property
    def body(self) -> str:
        return self.description


class Answer(ContentItem):
    """Its own content item, so votes, comments and moderation work unchanged. `title` copies the question's."""

    __tablename__ = "answers"
    __table_args__ = (
        # At most one accepted and one pinned answer per question.
        Index(
            "uq_answers_accepted",
            "question_id",
            unique=True,
            postgresql_where=text("accepted_at IS NOT NULL"),
        ),
        Index(
            "uq_answers_pinned",
            "question_id",
            unique=True,
            postgresql_where=text("pinned_at IS NOT NULL"),
        ),
    )
    __mapper_args__ = {"polymorphic_identity": ContentType.answer.value}

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def body(self) -> str:
        return self.description

    @property
    def accepted(self) -> bool:
        return self.accepted_at is not None

    @property
    def pinned(self) -> bool:
        return self.pinned_at is not None


class ReputationReason(enum.StrEnum):
    vote_up = "vote_up"
    vote_down = "vote_down"
    answer_accepted = "answer_accepted"  # your answer was accepted
    accepted_answer = "accepted_answer"  # you accepted someone's answer


class ReputationEvent(Base):
    """Reputation ledger. `event_key` makes every event idempotent: replaying it changes nothing."""

    __tablename__ = "reputation_events"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key"),
        CheckConstraint(_in("reason", ReputationReason), name="reason"),
        Index("ix_reputation_events_user_created", "user_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    event_key: Mapped[str] = mapped_column(String(100))
    reason: Mapped[str] = mapped_column(String(20))
    points: Mapped[int] = mapped_column(SmallInteger)
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = _now()


class NotificationKind(enum.StrEnum):
    reply = "reply"
    answer = "answer"
    answer_accepted = "answer_accepted"
    vote_milestone = "vote_milestone"
    moderation = "moderation"


class Notification(Base):
    """`call_number`/`title` are snapshots of the page to open (an answer points at its question)."""

    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "dedupe_key"),
        CheckConstraint(_in("kind", NotificationKind), name="kind"),
        Index("ix_notifications_user_created", "user_id", "created_at", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(16))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE")
    )
    call_number: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text, server_default="")
    dedupe_key: Mapped[str | None] = mapped_column(String(100))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    emailed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
