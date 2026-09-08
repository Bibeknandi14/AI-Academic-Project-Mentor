"""
User management endpoints.

Currently exposes:
  PATCH /users/me/mentor  — lets a student link (or change) their assigned mentor
                            by supplying a valid mentor code after registration.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember
from app.schemas.user import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


class MentorLinkRequest:
    """Pydantic model is defined inline to keep the schema file clean."""
    pass


from pydantic import BaseModel

class MentorCodeBody(BaseModel):
    mentor_code: str


@router.patch("/me/mentor", response_model=UserResponse)
async def link_mentor(
    body: MentorCodeBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Allows an authenticated student to link themselves to a mentor by code.
    Can be called at any point after registration — not just during sign-up.

    - Validates the mentor code exists and belongs to a MENTOR account.
    - Sets the student's assigned_mentor_id to that mentor's id.
    - Updates Project.mentor_id on ALL existing projects owned by this student.
    - Returns the updated user record.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can link to a mentor.")

    code = body.mentor_code.strip().upper()

    result = await db.execute(
        select(User).where(
            User.mentor_code == code,
            User.role == UserRole.MENTOR,
        )
    )
    mentor = result.scalars().first()
    if not mentor:
        raise HTTPException(
            status_code=404,
            detail=f"Mentor code '{code}' is invalid or does not belong to any mentor."
        )

    # Re-fetch the live student row so we can mutate it within this session.
    student_result = await db.execute(select(User).where(User.id == current_user.id))
    student = student_result.scalars().first()
    student.assigned_mentor_id = mentor.id

    # Propagate mentor assignment to ALL projects owned by this student
    proj_result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.user_id == current_user.id,
            ProjectMember.role == "OWNER",
        )
    )
    for proj in proj_result.scalars().all():
        proj.mentor_id = mentor.id

    await db.commit()
    await db.refresh(student)
    return student


@router.delete("/me/mentor", response_model=UserResponse)
async def unlink_mentor(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Removes an existing mentor assignment from the authenticated student
    and clears mentor_id on all projects owned by the student.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can unlink a mentor.")

    student_result = await db.execute(select(User).where(User.id == current_user.id))
    student = student_result.scalars().first()
    student.assigned_mentor_id = None

    # Clear mentor_id from all projects owned by this student
    proj_result = await db.execute(
        select(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(
            ProjectMember.user_id == current_user.id,
            ProjectMember.role == "OWNER",
        )
    )
    for proj in proj_result.scalars().all():
        proj.mentor_id = None

    await db.commit()
    await db.refresh(student)
    return student
