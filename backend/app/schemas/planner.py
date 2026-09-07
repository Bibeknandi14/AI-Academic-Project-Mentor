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
    tech_stack: Optional[List[str]] = Field(default=None, description="Optional student tech stack preference")
    duration_weeks: Optional[int] = 4
    team_size: Optional[int] = 2

class RoadmapGenerationOutput(BaseModel):
    identified_requirements: List[str] = Field(
        ...,
        description="Key technical requirements identified from the project idea (e.g. 'Semantic text embeddings & vector similarity', 'Relational CRUD storage, no ML needed', 'Image upload & CNN inference pipeline')"
    )
    suggested_tech_stack: List[str] = Field(
        ...,
        description="Curated, student-feasible technology stack tailored to the identified requirements (frontend, backend, database, and any necessary libraries/models)"
    )
    stack_rationale: str = Field(
        default="",
        description="Concise 2-3 sentence explanation confirming user-chosen technologies and explaining how supplementary architectural layers complete the solution"
    )
    project_summary: str = Field(..., description="Concise summary of the project architecture and workflow")
    recommended_architecture: str = Field(..., description="High-level architectural overview suitable for a student project")
    epics: List[PlannedEpic]
    tasks: List[PlannedTask]

