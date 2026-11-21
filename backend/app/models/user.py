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
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
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
        CheckConstraint(
            "graduation_year IS NULL OR graduation_year BETWEEN 1990 AND 2100",
            name="graduation_year",
        ),
        Index("ix_users_reputation", "reputation", "id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)  # stored lower-case
    display_name: Mapped[str] = mapped_column(String(80))
    # NULL for GPA sign-in accounts until they choose to set one via "forgot password".
    password_hash: Mapped[str | None] = mapped_column(String(255))
    gpa_id: Mapped[str | None] = mapped_column(String(32), unique=True)  # Unistra id
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
    bio: Mapped[str] = mapped_column(Text, server_default="")
    faculty: Mapped[str] = mapped_column(String(80), server_default="")
    graduation_year: Mapped[int | None] = mapped_column(SmallInteger)
    job_title: Mapped[str] = mapped_column(
        String(120), server_default=""
    )  # "current role"
    socials: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    # Look and links pulled from UFAZ GPA (see services/gpa_link.py); NULL until linked.
    gpa_profile: Mapped[dict | None] = mapped_column(JSONB)
    email_digest: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @property
    def avatar_url(self) -> str | None:
        from app.core.signing import sign_media

        if self.avatar_attachment_id:
            return sign_media(self.avatar_attachment_id, "sm")
        key = ((self.gpa_profile or {}).get("equipped") or {}).get("avatar")
        return f"{settings.GPA_URL.rstrip('/')}/api/avatars/{key}" if key else None

    @property
    def cosmetics(self) -> dict[str, str]:
        """GPA cosmetics Hub can draw: banner, frame and name effect (plus upgrade flags)."""
        eq = (self.gpa_profile or {}).get("equipped") or {}
        keep = ("banner", "banner_up", "frame", "frame_up", "name_effect")
        return {k: str(eq[k]) for k in keep if eq.get(k)}

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
