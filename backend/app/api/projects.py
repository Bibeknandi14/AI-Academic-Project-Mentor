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
from app.models.deletion_ticket import DeletionTicket
from app.models.notification import Notification
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.deletion_ticket import DeletionTicketCreate, DeletionTicketResponse

router = APIRouter(prefix="/projects", tags=["Projects"])


# ─── helpers ────────────────────────────────────────────────────────────────

async def _build_project_response(proj: Project, db: AsyncSession) -> ProjectResponse:
    """Compute and attach stats for a single project row."""
    t_total = await db.execute(
        select(func.count(Task.id)).where(Task.project_id == proj.id)
    )
    total_tasks = t_total.scalar() or 0

    t_done = await db.execute(
        select(func.count(Task.id)).where(
            Task.project_id == proj.id, Task.status == TaskStatus.DONE
        )
    )
    completed_tasks = t_done.scalar() or 0

    c_total = await db.execute(
        select(func.count(CommitLog.id)).where(CommitLog.project_id == proj.id)
    )
    commit_count = c_total.scalar() or 0

    latest_c = await db.execute(
        select(CommitLog)
        .where(CommitLog.project_id == proj.id)
        .order_by(CommitLog.commit_date.desc())
    )
    latest_commit = latest_c.scalars().first()

    is_at_risk = False
    if total_tasks > 0 and (completed_tasks / total_tasks) < 0.2:
        is_at_risk = True
    if latest_commit and (datetime.utcnow() - latest_commit.commit_date) > timedelta(days=3):
        is_at_risk = True

    return ProjectResponse(
        id=proj.id,
        title=proj.title,
        description=proj.description,
        github_repo=proj.github_repo,
        mentor_id=proj.mentor_id,
        status=proj.status,
        created_at=proj.created_at,
        completed_at=proj.completed_at,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        commit_count=commit_count,
        is_at_risk=is_at_risk,
    )


async def _assert_owner(project_id: str, user: User, db: AsyncSession) -> Project:
    """Return the project if the user is an OWNER member, else raise 403/404."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    mem = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
            ProjectMember.role == "OWNER",
        )
    )
    if not mem.scalars().first():
        raise HTTPException(status_code=403, detail="You are not an owner of this project")
    return proj


# ─── routes ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[ProjectResponse])
@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.MENTOR:
        result = await db.execute(
            select(Project)
            .outerjoin(ProjectMember, ProjectMember.project_id == Project.id)
            .outerjoin(User, User.id == ProjectMember.user_id)
            .where(
                (Project.mentor_id == current_user.id) |
                (User.assigned_mentor_id == current_user.id)
            )
            .distinct()
        )
    else:
        result = await db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == current_user.id)
        )
    projects = result.scalars().all()
    return [await _build_project_response(p, db) for p in projects]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve mentor_id: explicit → role-based → student's assigned mentor
    if project_in.mentor_id:
        mentor_id = project_in.mentor_id
    elif current_user.role == UserRole.MENTOR:
        mentor_id = current_user.id
    else:
        # Auto-link to assigned mentor if the student has one
        mentor_id = current_user.assigned_mentor_id

    project_id = str(uuid.uuid4())
    project = Project(
        id=project_id,
        title=project_in.title,
        description=project_in.description,
        github_repo=project_in.github_repo,
        mentor_id=mentor_id,
        status="active",
    )
    db.add(project)
    db.add(
        ProjectMember(
            id=str(uuid.uuid4()),
            project_id=project_id,
            user_id=current_user.id,
            role="OWNER",
        )
    )
    await db.commit()
    await db.refresh(project)
    return await _build_project_response(project, db)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a project's details (e.g., github_repo).
    Only an OWNER of the project can update it.
    """
    proj = await _assert_owner(project_id, current_user, db)

    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(proj, field, value)

    await db.commit()
    await db.refresh(proj)
    return await _build_project_response(proj, db)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return await _build_project_response(project, db)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalars().first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in project_in.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return await _build_project_response(project, db)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Direct deletion is only allowed when the project has NO assigned mentor.
    If a mentor is assigned the student must use POST /{id}/request-deletion
    to go through the ticket approval workflow instead.
    """
    proj = await _assert_owner(project_id, current_user, db)

    if proj.mentor_id:
        raise HTTPException(
            status_code=403,
            detail=(
                "This project has an assigned mentor. "
                "Please use POST /projects/{id}/request-deletion to submit a deletion request "
                "that the mentor must approve."
            ),
        )

    await db.delete(proj)
    await db.commit()
    return None


@router.post(
    "/{project_id}/request-deletion",
    response_model=DeletionTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_deletion(
    project_id: str,
    body: DeletionTicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student-only. Creates a DeletionTicket and sets project.status = pending_deletion.
    The project must be mentor-supervised and have no existing pending ticket.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can request project deletion.")

    proj = await _assert_owner(project_id, current_user, db)

    if not proj.mentor_id:
        raise HTTPException(
            status_code=400,
            detail="This project has no mentor assigned. You can delete it directly.",
        )

    if proj.status == "pending_deletion":
        raise HTTPException(
            status_code=409,
            detail="A deletion request is already pending for this project.",
        )

    # Prevent re-requesting on completed projects
    if proj.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot request deletion of a completed project.")

    ticket = DeletionTicket(
        id=str(uuid.uuid4()),
        project_id=project_id,
        student_id=current_user.id,
        mentor_id=proj.mentor_id,
        reason=body.reason,
        status="pending",
    )
    db.add(ticket)
    proj.status = "pending_deletion"

    # Notify the mentor about the new deletion request
    db.add(Notification(
        id=str(uuid.uuid4()),
        user_id=proj.mentor_id,
        type="deletion_request",
        message=f"{current_user.full_name} has requested deletion of '{proj.title}'. Please review under Deletion Requests.",
        related_project_id=project_id,
        is_read=False,
    ))

    await db.commit()
    await db.refresh(ticket)
    return ticket
