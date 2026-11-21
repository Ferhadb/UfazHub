"""Uploaded files. Bytes live in Storage (disk or S3); this row is the metadata."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import _now


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (CheckConstraint("kind IN ('image', 'file')", name="kind"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(5))
    mime: Mapped[str] = mapped_column(String(100))  # sniffed, never the client's claim
    size: Mapped[int] = mapped_column(BigInteger)
    original_name: Mapped[str] = mapped_column(String(255))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    # variant name -> {"key": storage key, "mime": ..., "width": ..., "height": ...}
    variants: Mapped[dict] = mapped_column(JSONB, server_default="{}")
    created_at: Mapped[datetime] = _now()
