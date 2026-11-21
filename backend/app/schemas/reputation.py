from datetime import datetime

from pydantic import BaseModel


class PointRule(BaseModel):
    reason: str
    label: str
    points: int


class PrivilegeRule(BaseModel):
    key: str
    label: str
    threshold: int


class ReputationRules(BaseModel):
    points: list[PointRule]
    privileges: list[PrivilegeRule]
    daily_vote_cap: int


class ReputationEventOut(BaseModel):
    reason: str
    points: int
    call_number: str | None = None
    title: str | None = None
    created_at: datetime
