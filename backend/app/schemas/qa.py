import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.content import AuthorOut, _clean


class QuestionIn(BaseModel):
    title: str = Field(min_length=10, max_length=200)
    body: str = Field(min_length=10, max_length=5000)
    topic: str = Field(min_length=2, max_length=60)
    linked_resource: str | None = Field(default=None, max_length=16)  # call number
    tags: list[str] = Field(default_factory=list, max_length=8)

    _clean_text = field_validator("title", "body", "topic")(_clean)


class AnswerIn(BaseModel):
    body: str = Field(min_length=10, max_length=10_000)  # plain text, rendered as text

    _clean_body = field_validator("body")(_clean)


class DuplicateIn(BaseModel):
    of: str = Field(min_length=1, max_length=16)  # call number of the original


class ItemRef(BaseModel):
    call_number: str
    title: str


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: Literal["question"]
    call_number: str
    title: str
    body: str
    topic: str
    status: str
    hidden_reason: str | None = None
    is_research: bool
    author: AuthorOut
    tags: list[str]
    vote_score: int
    bookmark_count: int
    comment_count: int
    answer_count: int = 0
    has_accepted: bool = False
    linked_resource: ItemRef | None = None
    duplicate_of: ItemRef | None = None
    created_at: datetime
    my_vote: Literal[-1, 0, 1] = 0
    bookmarked: bool = False

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        return [getattr(t, "name", t) for t in v]


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: Literal["answer"]
    call_number: str
    question_id: uuid.UUID
    body: str
    status: str
    hidden_reason: str | None = None
    author: AuthorOut
    vote_score: int
    comment_count: int
    accepted: bool
    pinned: bool
    created_at: datetime
    my_vote: Literal[-1, 0, 1] = 0
    bookmarked: bool = (
        False  # always false; shares `decorate` with the other content types
    )


class SimilarHit(BaseModel):
    call_number: str
    title: str
    answer_count: int
    has_accepted: bool
