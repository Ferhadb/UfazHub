import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.moderation import ReportReason
from app.models.user import Role, UserStatus
from app.schemas.auth import LoginIn
from app.schemas.content import AuthorOut

Reason = Field(min_length=3, max_length=500)


class ReportIn(BaseModel):
    reason: ReportReason
    note: str = Field(default="", max_length=1000)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    reason: str
    note: str
    status: str
    reporter: AuthorOut
    created_at: datetime


class QueueItem(BaseModel):
    id: uuid.UUID
    type: str
    call_number: str
    title: str
    status: str
    hidden_reason: str | None
    author: AuthorOut
    report_count: int
    reasons: list[str]
    created_at: datetime
    activity_at: datetime  # latest open report, submission or hide time (the sort key)


class ContentAction(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    action: Literal["hide", "unhide", "approve", "dismiss"]
    reason: str | None = Field(default=None, min_length=3, max_length=500)

    @model_validator(mode="after")
    def _reason_needed(self):
        if self.action in ("hide", "unhide") and not self.reason:
            raise ValueError("A reason is required to hide or unhide.")
        if len(set(self.ids)) != len(self.ids):
            raise ValueError("Duplicate ids.")
        return self


class ActionFailure(BaseModel):
    id: uuid.UUID
    message: str


class ActionResult(BaseModel):
    done: list[uuid.UUID]
    failed: list[ActionFailure]


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    status: str
    email_verified: bool
    reputation: int
    created_at: datetime


class UserStatusIn(BaseModel):
    status: UserStatus
    reason: str = Reason


class UserRoleIn(BaseModel):
    role: Role
    reason: str = Reason


class AuditOut(BaseModel):
    id: uuid.UUID
    actor: AuthorOut | None
    action: str
    target_type: str
    target_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    request_id: str | None
    created_at: datetime


class ItemRef(BaseModel):
    id: uuid.UUID
    call_number: str
    title: str
    status: str


class AppealIn(BaseModel):
    message: str = Field(min_length=10, max_length=1000)


class BanAppealIn(LoginIn):
    message: str = Field(min_length=10, max_length=1000)


class AppealOut(BaseModel):
    id: uuid.UUID
    kind: str
    status: str
    message: str
    response: str | None
    user: AuthorOut
    item: ItemRef | None
    created_at: datetime
    resolved_at: datetime | None


class AppealResolveIn(BaseModel):
    decision: Literal["accept", "reject"]
    response: str = Field(min_length=3, max_length=1000)


class ModerationEvent(BaseModel):
    """What the affected user sees: the action and the reason, never who took it."""

    id: uuid.UUID
    action: str
    reason: str | None
    created_at: datetime
    item: ItemRef | None
