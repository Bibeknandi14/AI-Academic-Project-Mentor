from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class SupervisorMessageBase(BaseModel):
    project_id: str
    message: str


class SupervisorMessageCreate(SupervisorMessageBase):
    """
    Sent by either a mentor or student.  sender_id is injected server-side
    from the authenticated user's JWT; receiver_id must be provided explicitly.
    """
    receiver_id: str


class SupervisorMessageResponse(SupervisorMessageBase):
    id: str
    sender_id: str
    receiver_id: str
    created_at: datetime

    model_config = {"from_attributes": True}
