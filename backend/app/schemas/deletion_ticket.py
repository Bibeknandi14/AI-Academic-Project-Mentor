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


class RejectionBody(BaseModel):
    """Body for the reject endpoint — lets the mentor supply a reason."""
    rejection_note: str


class DeletionTicketResponse(DeletionTicketBase):
    id: str
    student_id: str
    mentor_id: str
    status: TicketStatus
    rejection_note: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
