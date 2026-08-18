from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class MentorshipQueryInput(BaseModel):
    project_id: str
    active_task_id: Optional[str] = None
    question: str

class InjectedContextSummary(BaseModel):
    active_task: Optional[Dict[str, Any]] = None
    recent_commits: Optional[List[Dict[str, Any]]] = None
    tech_stack: Optional[List[str]] = None

class ChatMessageResponse(BaseModel):
    id: str
    project_id: str
    user_id: str
    task_id: Optional[str] = None
    sender: str
    message: str
    context_used: Optional[InjectedContextSummary] = None
    created_at: datetime

    model_config = {"from_attributes": True}
