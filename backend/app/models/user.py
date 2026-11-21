import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(enum.StrEnum):
    user = "user"
    verified_ufazian = "verified_ufazian"
    admin = "admin"


class UserStatus(enum.StrEnum):
    active = "active"
    muted = "muted"
    banned = "banned"


def _in(column: str, enum_cls: type[enum.StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(m.value) for m in enum_cls)})"


def _now():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(_in("role", Role), name="role"),
        CheckConstraint(_in("status", UserStatus), name="status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)  # stored lower-case
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), server_default=Role.user.value)
    status: Mapped[str] = mapped_column(
        String(10), server_default=UserStatus.active.value
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avatar_attachment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attachments.id", ondelete="SET NULL", use_alter=True)
    )
    # Sum of the user's reputation_events; only app.services.reputation writes it.
    reputation: Mapped[int] = mapped_column(Integer, server_default="0")
    email_digest: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def avatar_url(self) -> str | None:
        from app.core.signing import sign_media

        return (
            sign_media(self.avatar_attachment_id, "sm")
            if self.avatar_attachment_id
            else None
        )

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None


class RefreshToken(Base):
    """Server-side record of an issued refresh token (only its SHA-256 is stored).

    Rotation marks the row `used_at`; presenting a used/revoked token again means
    theft, so the whole family is revoked.
    """

    __tablename__ = "refresh_tokens"
    __table_args__ = (Index("ix_refresh_tokens_family_id", "family_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()


class AuthToken(Base):
    """One-time email-verification and password-reset tokens (hashed, expiring)."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint("kind IN ('verify_email', 'reset_password')", name="kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
