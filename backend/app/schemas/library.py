"""Shapes for courses, research, people, follows and reading lists."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.urls import canonical_url
from app.schemas.content import AuthorOut

CardType = Literal["resource", "article", "collection", "question"]


class ItemCard(BaseModel):
    """A content item as a catalogue card; every cross-type list returns these."""

    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    type: CardType
    call_number: str
    title: str
    description: str
    is_research: bool
    author: AuthorOut
    tags: list[str]
    vote_score: int
    comment_count: int
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def _tag_names(cls, v):
        return [getattr(t, "name", t) for t in v]

    @field_validator("description")
    @classmethod
    def _short(cls, v: str) -> str:
        return v if len(v) <= 240 else v[:239].rstrip() + "…"


# --- courses -----------------------------------------------------------------------
class ProgramRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    level: str
    description: str
    program: ProgramRef


class CourseDetail(CourseOut):
    item_count: int
    start_here: list[ItemCard]  # ordered path, at most MAX_PATH


class ProgramOut(ProgramRef):
    description: str
    courses: list[CourseOut]


class ProgramIn(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=48)
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=1000)


class CourseIn(BaseModel):
    program_slug: str = Field(max_length=48)
    slug: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=64)
    name: str = Field(min_length=2, max_length=120)
    level: Literal["L1", "L2", "L3", "M1", "M2"]
    description: str = Field(default="", max_length=1000)


class PathIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(max_length=20)


class AttachIn(BaseModel):
    course_slugs: list[str] = Field(max_length=5)


# --- people ------------------------------------------------------------------------
class Socials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    github: str | None = Field(default=None, max_length=200)
    linkedin: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=200)
    x: str | None = Field(default=None, max_length=200)

    @field_validator("*")
    @classmethod
    def _http_only(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip()
        canonical_url(v)  # raises ValueError -> 422 with the field name
        return v


class ProfilePatch(BaseModel):
    """Only the fields sent change."""

    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=500)
    faculty: str | None = Field(default=None, max_length=80)
    graduation_year: int | None = Field(default=None, ge=1990, le=2100)
    job_title: str | None = Field(default=None, max_length=120)
    socials: Socials | None = None


class PersonCard(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    avatar_url: str | None = None
    reputation: int
    role: str
    faculty: str
    graduation_year: int | None
    job_title: str


class Badge(BaseModel):
    slug: str
    name: str
    description: str


class DayCount(BaseModel):
    day: date
    count: int


class Profile(PersonCard):
    bio: str
    socials: dict[str, str]
    joined_at: datetime
    counts: dict[
        str, int
    ]  # published items by type, plus "research" and "accepted_answers"
    badges: list[Badge]
    activity: list[DayCount]  # one row per active day of the last 365


class LeaderRow(BaseModel):
    rank: int
    points: int
    person: PersonCard


# --- follows -----------------------------------------------------------------------
class FollowedTag(BaseModel):
    name: str
    slug: str


class FollowOut(BaseModel):
    following: bool


# --- reading lists -----------------------------------------------------------------
class ListIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class ReadingListOut(BaseModel):
    id: uuid.UUID
    name: str
    share_token: str | None
    item_count: int
    created_at: datetime


class SharedList(BaseModel):
    name: str
    owner: AuthorOut
    items: list[ItemCard]
    next_cursor: str | None = None
