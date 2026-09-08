from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel

# Valid ticket statuses — mirrors the DB check constraint.
TicketStatus = Literal["pending", "approved", "rejected"]


class DeletionTicketBase(BaseModel):
    project_id: str
    reason: str


class DeletionTicketCreate(DeletionTicketBase):
    """
    Submitted by a student.  mentor_id is resolved server-side from
    the project's mentor_id field; students do not supply it directly.
    """
    pass


class DeletionTicketUpdate(BaseModel):
    """Used by a mentor to approve or reject a pending ticket."""
    status: TicketStatus


class DeletionTicketResponse(DeletionTicketBase):
    id: str
    student_id: str
    mentor_id: str
    status: TicketStatus
    created_at: datetime

    model_config = {"from_attributes": True}
