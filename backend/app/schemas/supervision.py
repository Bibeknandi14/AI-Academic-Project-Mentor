from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class ProjectSummary(BaseModel):
    """Lightweight project view embedded inside a student summary."""
    id: str
    title: str
    status: str
    github_repo: Optional[str] = None
    mentor_id: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    commit_count: int = 0
    latest_commit_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_at_risk: bool = False

    model_config = {"from_attributes": True}


class StudentSummary(BaseModel):
    """
    A student record visible only to their assigned mentor.
    Returned by GET /supervision/students.
    """
    id: str
    full_name: str
    email: str
    github_username: Optional[str] = None
    assigned_mentor_id: Optional[str] = None
    projects: List[ProjectSummary] = []

    model_config = {"from_attributes": True}
