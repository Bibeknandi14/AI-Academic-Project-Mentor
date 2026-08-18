from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class ProjectBase(BaseModel):
    title: str
    description: Optional[str] = None
    github_repo: Optional[str] = None

class ProjectCreate(ProjectBase):
    mentor_id: Optional[str] = None

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    github_repo: Optional[str] = None
    mentor_id: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    mentor_id: Optional[str] = None
    created_at: datetime
    total_tasks: Optional[int] = 0
    completed_tasks: Optional[int] = 0
    commit_count: Optional[int] = 0
    is_at_risk: Optional[bool] = False

    model_config = {"from_attributes": True}
