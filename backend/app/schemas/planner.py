from typing import List, Optional
from pydantic import BaseModel, Field

class PlannedTask(BaseModel):
    title: str = Field(..., description="Short task title")
    description: str = Field(..., description="Detailed technical work required")
    epic_name: str = Field(..., description="High level epic grouping")
    sprint_name: str = Field(..., description="Target sprint (e.g. Sprint 1)")
    priority: str = Field(default="MEDIUM", description="LOW, MEDIUM, or HIGH")
    git_branch_suggestion: Optional[str] = Field(default=None, description="Suggested git branch name")

class PlannedEpic(BaseModel):
    name: str
    description: str

class RoadmapGenerationInput(BaseModel):
    idea_title: str
    idea_description: str
    tech_stack: Optional[List[str]] = ["React", "FastAPI", "PostgreSQL"]
    duration_weeks: Optional[int] = 4
    team_size: Optional[int] = 2

class RoadmapGenerationOutput(BaseModel):
    project_summary: str
    recommended_architecture: str
    epics: List[PlannedEpic]
    tasks: List[PlannedTask]
