import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.content import ContentType
from app.schemas.content import AuthorOut, _clean


class CollectionItemIn(BaseModel):
    item_id: uuid.UUID
    note: str = Field(default="", max_length=500)

    _clean_note = field_validator("note")(_clean)


class CollectionIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    is_research: bool = False
    tags: list[str] = Field(default_factory=list, max_length=8)
    items: list[CollectionItemIn] = Field(min_length=1, max_length=50)

    _clean_text = field_validator("title", "description")(_clean)


class CollectionPatch(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    is_research: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=8)
    items: list[CollectionItemIn] | None = Field(
        default=None, min_length=1, max_length=50
    )

    _clean_text = field_validator("title", "description")(_clean)


class ItemRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: ContentType
    call_number: str
    title: str
    description: str
    is_research: bool
    vote_score: int


class CollectionItemOut(BaseModel):
    position: int
    note: str
    item: ItemRef


class CollectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: Literal["collection"]
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
    items: list[CollectionItemOut]  # published items only
    created_at: datetime
    my_vote: Literal[-1, 0, 1] = 0
    bookmarked: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        return [getattr(t, "name", t) for t in v]
