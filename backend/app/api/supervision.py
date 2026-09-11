"""
Mentor supervision endpoints.

All student-facing queries are explicitly filtered by assigned_mentor_id == current_mentor.id
server-side. A mentor CANNOT access data for students not assigned to them.
"""
import uuid
from typing import List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.deps import get_db, get_current_user, get_current_mentor
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.models.task import Task, TaskStatus
from app.models.commit import CommitLog
from app.models.supervisor_message import SupervisorMessage
from app.models.mentor_activity_log import MentorActivityLog
from app.models.notification import Notification
from app.schemas.supervision import StudentSummary, ProjectSummary
from app.schemas.supervisor_message import SupervisorMessageCreate, SupervisorMessageResponse
from app.schemas.mentor_activity_log import MentorActivityLogResponse

router = APIRouter(prefix="/supervision", tags=["Supervision"])


# ─── helpers ─────────────────────────────────────────────────────────────────

async def _project_summary(proj: Project, db: AsyncSession) -> ProjectSummary:
    t_total = (await db.execute(
        select(func.count(Task.id)).where(Task.project_id == proj.id)
    )).scalar() or 0

    t_done = (await db.execute(
        select(func.count(Task.id)).where(
            Task.project_id == proj.id, Task.status == TaskStatus.DONE
        )
    )).scalar() or 0

    c_total = (await db.execute(
        select(func.count(CommitLog.id)).where(CommitLog.project_id == proj.id)
    )).scalar() or 0

    latest_c = (await db.execute(
        select(CommitLog)
        .where(CommitLog.project_id == proj.id)
        .order_by(CommitLog.commit_date.desc())
    )).scalars().first()

    is_at_risk = False
    if t_total > 0 and (t_done / t_total) < 0.2:
        is_at_risk = True
    if latest_c and (datetime.utcnow() - latest_c.commit_date) > timedelta(days=3):
        is_at_risk = True

    return ProjectSummary(
        id=proj.id,
        title=proj.title,
        status=proj.status,
        github_repo=proj.github_repo,
        mentor_id=proj.mentor_id,
        completed_at=proj.completed_at,
        total_tasks=t_total,
        completed_tasks=t_done,
        commit_count=c_total,
        latest_commit_date=latest_c.commit_date if latest_c else None,
        is_at_risk=is_at_risk,
    )


async def _assert_mentor_owns_project(project_id: str, mentor: User, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    proj = result.scalars().first()
    if not proj or proj.mentor_id != mentor.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


# ─── student list ─────────────────────────────────────────────────────────────

@router.get("/students", response_model=List[StudentSummary])
async def list_my_students(
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """
    Returns students where assigned_mentor_id == current_mentor.id,
    each enriched with their project summaries.
    Explicit server-side filter — no other mentor's students are included.
    Automatically ensures student's projects are synced with mentor_id.
    """
    result = await db.execute(
        select(User).where(
            User.assigned_mentor_id == mentor.id,
            User.role == UserRole.STUDENT,
        )
    )
    students = result.scalars().all()

    summaries: List[StudentSummary] = []
    projects_updated = False

    for student in students:
        # Get projects this student owns
        proj_result = await db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                ProjectMember.user_id == student.id,
                ProjectMember.role == "OWNER",
            )
        )
        projects = proj_result.scalars().all()

        # Ensure project.mentor_id is in sync with the student's assigned mentor
        for p in projects:
            if p.mentor_id != mentor.id:
                p.mentor_id = mentor.id
                projects_updated = True

        project_summaries = [await _project_summary(p, db) for p in projects]

        summaries.append(
            StudentSummary(
                id=student.id,
                full_name=student.full_name,
                email=student.email,
                github_username=student.github_username,
                assigned_mentor_id=student.assigned_mentor_id,
                projects=project_summaries,
            )
        )

    if projects_updated:
        await db.commit()

    return summaries


# ─── mentor actions ───────────────────────────────────────────────────────────

@router.patch("/projects/{project_id}/complete", response_model=ProjectSummary)
async def mark_project_complete(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """Mark a supervised project as completed. Only the project's assigned mentor can do this."""
    proj = await _assert_mentor_owns_project(project_id, mentor, db)
    proj.status = "completed"
    proj.completed_at = datetime.utcnow()

    # Find the student owner for the activity log and notification
    owner_res = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.role == "OWNER",
        )
    )
    owner = owner_res.scalars().first()

    db.add(MentorActivityLog(
        id=str(uuid.uuid4()),
        mentor_id=mentor.id,
        action_type="marked_completed",
        student_id=owner.user_id if owner else None,
        project_id=project_id,
        detail=f"Marked project '{proj.title}' as completed.",
    ))

    if owner:
        db.add(Notification(
            id=str(uuid.uuid4()),
            user_id=owner.user_id,
            related_project_id=project_id,
            type="project_completed",
            message=f"Your mentor marked project '{proj.title}' as completed.",
        ))

    await db.commit()
    await db.refresh(proj)
    return await _project_summary(proj, db)


@router.patch("/students/{student_id}/unassign", response_model=dict)
async def unassign_student(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """
    Remove the mentor assignment from a student.
    Only the student's current assigned mentor can do this.
    Also clears mentor_id from all projects owned by the student.
    """
    result = await db.execute(
        select(User).where(
            User.id == student_id,
            User.assigned_mentor_id == mentor.id,  # explicit ownership check
        )
    )
    student = result.scalars().first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or not assigned to you")

    student.assigned_mentor_id = None

    # Clear mentor_id on the student's projects
    proj_result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.user_id == student_id,
            ProjectMember.role == "OWNER",
        )
    )
    for proj in proj_result.scalars().all():
        if proj.mentor_id == mentor.id:
            proj.mentor_id = None

    db.add(MentorActivityLog(
        id=str(uuid.uuid4()),
        mentor_id=mentor.id,
        action_type="unassigned_student",
        student_id=student_id,
        project_id=None,
        detail=f"Unassigned student '{student.full_name}' ({student.email})",
    ))

    await db.commit()
    return {"detail": f"Student '{student.full_name}' has been unassigned."}


# ─── supervision messages ─────────────────────────────────────────────────────

@router.get("/messages/{project_id}", response_model=List[SupervisorMessageResponse])
async def get_supervision_messages(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the full message history for a project's supervision thread.
    Accessible by the project's mentor or any OWNER member of the project.
    """
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    proj = proj_result.scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find owner of the project
    owner_result = await db.execute(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.role == "OWNER",
        )
    )
    owner = owner_result.scalars().first()

    # Access check: must be the assigned mentor OR an OWNER member
    is_mentor = current_user.role == UserRole.MENTOR and (
        proj.mentor_id == current_user.id or (owner and owner.assigned_mentor_id == current_user.id)
    )
    if not is_mentor:
        mem = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        if not mem.scalars().first():
            raise HTTPException(status_code=403, detail="Access denied")

    # Auto-sync project.mentor_id if missing but owner is assigned to a mentor
    if not proj.mentor_id and owner and owner.assigned_mentor_id:
        proj.mentor_id = owner.assigned_mentor_id
        await db.commit()

    result = await db.execute(
        select(SupervisorMessage)
        .where(SupervisorMessage.project_id == project_id)
        .order_by(SupervisorMessage.created_at.asc())
    )
    return result.scalars().all()


@router.post(
    "/messages/{project_id}",
    response_model=SupervisorMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_supervision_message(
    project_id: str,
    body: SupervisorMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Send a supervision message.  receiver_id is resolved server-side:
      - If sender is mentor  → receiver is the OWNER student of the project.
      - If sender is student → receiver is the project's mentor or student's assigned mentor.
    The body's receiver_id field is used as an override only if auto-resolution fails.
    """
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    proj = proj_result.scalars().first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find owner of the project
    owner_result = await db.execute(
        select(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.role == "OWNER",
        )
    )
    owner = owner_result.scalars().first()

    is_mentor = current_user.role == UserRole.MENTOR and (
        proj.mentor_id == current_user.id or (owner and owner.assigned_mentor_id == current_user.id)
    )
    is_member = False
    if not is_mentor:
        mem = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user.id,
            )
        )
        is_member = mem.scalars().first() is not None

    if not is_mentor and not is_member:
        raise HTTPException(status_code=403, detail="Access denied")

    # Auto-resolve receiver
    if is_mentor:
        # receiver = the student OWNER
        receiver_id = owner.id if owner else body.receiver_id
    else:
        # receiver = the project mentor or student's assigned mentor
        target_mentor_id = proj.mentor_id or current_user.assigned_mentor_id or (owner.assigned_mentor_id if owner else None)
        if not target_mentor_id:
            raise HTTPException(
                status_code=400,
                detail="This project has no mentor assigned — cannot send supervision message.",
            )
        receiver_id = target_mentor_id
        if not proj.mentor_id:
            proj.mentor_id = target_mentor_id

    msg = SupervisorMessage(
        id=str(uuid.uuid4()),
        project_id=project_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        message=body.message,
    )
    db.add(msg)

    # Notify the recipient of the new supervision message
    db.add(Notification(
        id=str(uuid.uuid4()),
        user_id=receiver_id,
        type="supervision_message",
        message=f"New supervision message from {current_user.full_name}: \"{body.message[:80]}{'...' if len(body.message) > 80 else ''}\"",
        related_project_id=project_id,
        is_read=False,
    ))

    await db.commit()
    await db.refresh(msg)
    return msg


# ─── activity log ─────────────────────────────────────────────────────────────

@router.get("/activity-log", response_model=List[MentorActivityLogResponse])
async def get_activity_log(
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """
    Returns the authenticated mentor's full activity history across ALL their students,
    sorted newest-first. Filtered strictly to mentor_id == current_user.id.
    """
    result = await db.execute(
        select(MentorActivityLog)
        .where(MentorActivityLog.mentor_id == mentor.id)
        .order_by(MentorActivityLog.created_at.desc())
    )
    return result.scalars().all()
