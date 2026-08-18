import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.planner import RoadmapGenerationInput, RoadmapGenerationOutput
from app.services.llm_service import get_llm_provider

router = APIRouter(prefix="/planner", tags=["AI Roadmap Planner"])

@router.post("/generate", response_model=RoadmapGenerationOutput)
async def generate_roadmap(
    input_data: RoadmapGenerationInput,
    current_user: User = Depends(get_current_user)
):
    llm = get_llm_provider()
    
    prompt = (
        f"Act as a Senior Agile Project Manager and Lead Architect.\n"
        f"Create a structured technical sprint roadmap for a student academic project.\n\n"
        f"Project Title: {input_data.idea_title}\n"
        f"Project Description: {input_data.idea_description}\n"
        f"Target Tech Stack: {', '.join(input_data.tech_stack or [])}\n"
        f"Duration: {input_data.duration_weeks} weeks\n"
        f"Team Size: {input_data.team_size} students\n\n"
        f"Provide epics and detailed, actionable tasks split across sprints."
    )
    
    try:
        output = await llm.generate_structured_json(
            prompt=prompt,
            response_schema=RoadmapGenerationOutput,
            system_instruction="You are an expert AI software architect creating strict JSON Agile project roadmaps."
        )
        return output
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Roadmap generation failed: {str(e)}"
        )

@router.post("/convert-to-project", status_code=status.HTTP_201_CREATED)
async def convert_roadmap_to_project(
    roadmap_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    title = roadmap_data.get("idea_title") or "New AI Planned Project"
    description = roadmap_data.get("project_summary") or roadmap_data.get("idea_description")
    
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        title=title,
        description=description,
        github_repo=roadmap_data.get("github_repo")
    )
    db.add(project)

    member = ProjectMember(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=current_user.id,
        role="OWNER"
    )
    db.add(member)

    # Add tasks
    tasks = roadmap_data.get("tasks", [])
    created_tasks = []
    for t in tasks:
        p_val = t.get("priority", "MEDIUM").upper()
        p_enum = TaskPriority.MEDIUM
        if p_val == "HIGH":
            p_enum = TaskPriority.HIGH
        elif p_val == "LOW":
            p_enum = TaskPriority.LOW

        task = Task(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=t.get("title", "Untitled Task"),
            description=t.get("description", ""),
            epic_name=t.get("epic_name", "Core"),
            sprint_name=t.get("sprint_name", "Sprint 1"),
            status=TaskStatus.TODO,
            priority=p_enum,
            assigned_user_id=current_user.id,
            git_branch=t.get("git_branch_suggestion")
        )
        db.add(task)
        created_tasks.append(task)

    await db.commit()
    return {"project_id": project_id, "title": title, "task_count": len(created_tasks)}
