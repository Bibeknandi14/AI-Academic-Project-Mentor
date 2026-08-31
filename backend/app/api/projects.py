import uuid
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus
from app.models.commit import CommitLog
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.MENTOR:
        result = await db.execute(select(Project).where(Project.mentor_id == current_user.id))
        projects = result.scalars().all()
    else:
        # Get projects user is member of or created
        result = await db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == current_user.id)
        )
        projects = result.scalars().all()

    project_list = []
    for proj in projects:
        # Calculate stats
        t_total = await db.execute(select(func.count(Task.id)).where(Task.project_id == proj.id))
        total_tasks = t_total.scalar() or 0
        
        t_done = await db.execute(select(func.count(Task.id)).where(Task.project_id == proj.id, Task.status == TaskStatus.DONE))
        completed_tasks = t_done.scalar() or 0

        c_total = await db.execute(select(func.count(CommitLog.id)).where(CommitLog.project_id == proj.id))
        commit_count = c_total.scalar() or 0

        # Check at-risk status: no commits in last 3 days or <20% done with tasks
        latest_c = await db.execute(select(CommitLog).where(CommitLog.project_id == proj.id).order_by(CommitLog.commit_date.desc()))
        latest_commit = latest_c.scalars().first()
        
        is_at_risk = False
        if total_tasks > 0 and (completed_tasks / total_tasks) < 0.2:
            is_at_risk = True
        if latest_commit and (datetime.utcnow() - latest_commit.commit_date) > timedelta(days=3):
            is_at_risk = True

        p_resp = ProjectResponse(
            id=proj.id,
            title=proj.title,
            description=proj.description,
            github_repo=proj.github_repo,
            mentor_id=proj.mentor_id,
            created_at=proj.created_at,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            commit_count=commit_count,
            is_at_risk=is_at_risk
        )
        project_list.append(p_resp)
        
    return project_list

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        title=project_in.title,
        description=project_in.description,
        github_repo=project_in.github_repo,
        mentor_id=project_in.mentor_id if project_in.mentor_id else (current_user.id if current_user.role == UserRole.MENTOR else None)
    )
    db.add(project)

    member = ProjectMember(
        id=str(uuid.uuid4()),
        project_id=project_id,
        user_id=current_user.id,
        role="OWNER"
    )
    db.add(member)

    await db.commit()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        github_repo=project.github_repo,
        mentor_id=project.mentor_id,
        created_at=project.created_at,
        total_tasks=0,
        completed_tasks=0,
        commit_count=0,
        is_at_risk=False
    )

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    t_total = await db.execute(select(func.count(Task.id)).where(Task.project_id == project.id))
    total_tasks = t_total.scalar() or 0
    
    t_done = await db.execute(select(func.count(Task.id)).where(Task.project_id == project.id, Task.status == TaskStatus.DONE))
    completed_tasks = t_done.scalar() or 0

    c_total = await db.execute(select(func.count(CommitLog.id)).where(CommitLog.project_id == project.id))
    commit_count = c_total.scalar() or 0

    return ProjectResponse(
        id=project.id,
        title=project.title,
        description=project.description,
        github_repo=project.github_repo,
        mentor_id=project.mentor_id,
        created_at=project.created_at,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        commit_count=commit_count,
        is_at_risk=False
    )
