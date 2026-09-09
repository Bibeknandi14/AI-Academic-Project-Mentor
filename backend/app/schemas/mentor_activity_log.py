from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel

ActionType = Literal[
    "approved_deletion",
    "rejected_deletion",
    "marked_completed",
    "unassigned_student",
]


class MentorActivityLogResponse(BaseModel):
    id: str
    mentor_id: str
    action_type: ActionType
    student_id: Optional[str] = None
    project_id: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
