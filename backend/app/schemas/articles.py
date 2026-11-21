import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.media import Attachment
from app.schemas.content import AuthorOut, _clean
from app.schemas.media import AttachmentOut

_TEXT = ("title", "excerpt")


class ArticleIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body_md: str = Field(min_length=20, max_length=60_000)
    excerpt: str = Field(default="", max_length=300)  # empty: taken from the body
    cover_attachment_id: uuid.UUID | None = None
    is_research: bool = False
    tags: list[str] = Field(default_factory=list, max_length=8)
    publish: bool = False  # false keeps it a private draft

    _clean_text = field_validator(*_TEXT)(_clean)


class ArticlePatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    body_md: str | None = Field(default=None, min_length=20, max_length=60_000)
    excerpt: str | None = Field(default=None, max_length=300)
    cover_attachment_id: uuid.UUID | None = None
    is_research: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=8)
    publish: bool | None = None

    _clean_text = field_validator(*_TEXT)(_clean)


class PreviewIn(BaseModel):
    body_md: str = Field(max_length=60_000)


class TocEntry(BaseModel):
    level: Literal[2, 3]
    text: str


class PreviewOut(BaseModel):
    body_html: str
    toc: list[TocEntry]
    reading_minutes: int


class ArticleCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: Literal["article"]
    call_number: str
    slug: str
    title: str
    excerpt: str
    status: str
    hidden_reason: str | None = None
    is_research: bool
    author: AuthorOut
    tags: list[str]
    vote_score: int
    bookmark_count: int
    comment_count: int
    view_count: int
    reading_minutes: int
    cover: AttachmentOut | None = None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    my_vote: Literal[-1, 0, 1] = 0
    bookmarked: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        return [getattr(t, "name", t) for t in v]

    @field_validator("cover", mode="before")
    @classmethod
    def _cover(cls, v):
        return AttachmentOut.of(v) if isinstance(v, Attachment) else v


class ArticleOut(ArticleCard):
    body_html: str
    toc: list[TocEntry]
    body_md: str | None = None  # only for the author and admins (the editor needs it)
