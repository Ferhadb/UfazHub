import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.content import AuthorOut


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    kind: str
    actor: AuthorOut | None = None
    call_number: str  # the page to open (an answer points at its question)
    title: str
    message: str
    read: bool
    created_at: datetime


class ReadIn(BaseModel):
    ids: list[uuid.UUID] | None = None  # null marks everything read


class UnreadOut(BaseModel):
    unread: int


class NotificationSettings(BaseModel):
    email_digest: bool
