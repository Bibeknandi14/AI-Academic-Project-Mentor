from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.models.task import TaskStatus, TaskPriority

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    epic_name: Optional[str] = "Core Features"
    sprint_name: Optional[str] = "Sprint 1"
    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_user_id: Optional[str] = None
    git_branch: Optional[str] = None

class TaskCreate(TaskBase):
    project_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    epic_name: Optional[str] = None
    sprint_name: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assigned_user_id: Optional[str] = None
    git_branch: Optional[str] = None

class TaskResponse(TaskBase):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
