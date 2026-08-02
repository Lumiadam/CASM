from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ChangeAction, ChangeRequestStatus, ChangeTarget


class ChangeRequestCreate(BaseModel):
    target_type: ChangeTarget
    action: ChangeAction
    target_id: int | None = None
    payload_json: dict = Field(default_factory=dict)


class ChangeRequestReview(BaseModel):
    approved: bool
    reason: str = Field(min_length=1, max_length=2000)


class ChangeRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: ChangeTarget
    action: ChangeAction
    target_id: int | None
    payload_json: dict
    status: ChangeRequestStatus
    requester_id: int
    reviewer_id: int | None
    review_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
