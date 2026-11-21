import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.content import AuthorOut, _clean


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: uuid.UUID | None = None

    _clean_body = field_validator("body")(_clean)

    @field_validator("body")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v:
            raise ValueError("Comment cannot be empty")
        return v


class CommentOut(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    parent_id: uuid.UUID | None
    author: AuthorOut
    body: str  # plain text: clients must render it as text, never as HTML
    created_at: datetime
    replies: list["CommentOut"] = []
