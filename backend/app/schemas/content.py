import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.urls import canonical_url
from app.models.content import Difficulty, ResourceType
from app.models.media import Attachment
from app.schemas.media import AttachmentOut

Text = Field(default="", max_length=2000)
# C0 controls would collide with the highlight markers (U+0002/U+0003) and are never legitimate text.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _clean(cls, v):
    return _CONTROL.sub("", v).strip() if isinstance(v, str) else v


class AuthorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    avatar_url: str | None = None  # signed, expiring
    reputation: int = 0
    cosmetics: dict[str, str] = {}


class LinkIn(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    label: str = Field(default="", max_length=120)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        v = v.strip()
        canonical_url(v)  # raises ValueError -> 422 with the field name
        return v


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    url: str
    label: str
    preview_title: str | None = None
    preview_image: str | None = None  # remote URL from the page's og:image
    preview_favicon: str | None = None
    health: Literal["ok", "reported", "dead"] = "ok"


class ResourceIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    resource_type: ResourceType
    category: str = Field(default="", max_length=60)
    difficulty: Difficulty
    time_commitment_minutes: int | None = Field(default=None, ge=0, le=100_000)
    prerequisites: str = Text
    best_part: str = Text
    warning: str = Text
    student_note: str = Text
    is_research: bool = False
    links: list[LinkIn] = Field(min_length=1, max_length=5)
    tags: list[str] = Field(default_factory=list, max_length=8)
    primary_attachment_id: uuid.UUID | None = None

    _clean_text = field_validator(
        "title",
        "description",
        "category",
        "prerequisites",
        "best_part",
        "warning",
        "student_note",
    )(_clean)


class ResourcePatch(BaseModel):
    """Every field optional; only the ones sent change."""

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=10, max_length=2000)
    resource_type: ResourceType | None = None
    category: str | None = Field(default=None, max_length=60)
    difficulty: Difficulty | None = None
    time_commitment_minutes: int | None = Field(default=None, ge=0, le=100_000)
    prerequisites: str | None = Field(default=None, max_length=2000)
    best_part: str | None = Field(default=None, max_length=2000)
    warning: str | None = Field(default=None, max_length=2000)
    student_note: str | None = Field(default=None, max_length=2000)
    is_research: bool | None = None
    links: list[LinkIn] | None = Field(default=None, min_length=1, max_length=5)
    tags: list[str] | None = Field(default=None, max_length=8)
    primary_attachment_id: uuid.UUID | None = None

    _clean_text = field_validator(
        "title",
        "description",
        "category",
        "prerequisites",
        "best_part",
        "warning",
        "student_note",
    )(_clean)


class ResourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: Literal["resource"]
    call_number: str
    title: str
    description: str
    status: str
    hidden_reason: str | None = None
    is_research: bool
    author: AuthorOut
    tags: list[str]
    vote_score: int
    bookmark_count: int
    comment_count: int
    view_count: int
    resource_type: ResourceType
    category: str
    difficulty: Difficulty
    time_commitment_minutes: int | None
    prerequisites: str
    best_part: str
    warning: str
    student_note: str
    links: list[LinkOut]
    attachment: AttachmentOut | None = None
    created_at: datetime
    my_vote: Literal[-1, 0, 1] = 0
    bookmarked: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        return [getattr(t, "name", t) for t in v]

    @field_validator("attachment", mode="before")
    @classmethod
    def _attachment(cls, v):
        return AttachmentOut.of(v) if isinstance(v, Attachment) else v


class VoteIn(BaseModel):
    value: Literal[-1, 0, 1]  # 0 removes the vote


class VoteOut(BaseModel):
    vote_score: int
    my_vote: Literal[-1, 0, 1]


class BookmarkOut(BaseModel):
    bookmark_count: int
    bookmarked: bool


class HideIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class TagOut(BaseModel):
    name: str
    slug: str
    count: int


class DuplicateHit(BaseModel):
    call_number: str
    title: str
    match: Literal["same_link", "similar_title"]


class SearchHit(BaseModel):
    id: uuid.UUID
    type: Literal[
        "resource", "article", "collection", "question"
    ]  # answers live on questions
    call_number: str
    title: str
    # Highlights are wrapped in U+0002 / U+0003, never HTML, so clients render them without risk.
    title_hl: str
    snippet: str
    is_research: bool
    vote_score: int
    created_at: datetime
