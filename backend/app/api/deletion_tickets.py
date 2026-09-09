import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_mentor, get_current_user
from app.models.user import User, UserRole
from app.models.project import Project
from app.models.deletion_ticket import DeletionTicket
from app.models.mentor_activity_log import MentorActivityLog
from app.models.notification import Notification
from app.schemas.deletion_ticket import DeletionTicketResponse, RejectionBody

router = APIRouter(prefix="/deletion-tickets", tags=["Deletion Tickets"])


def _own_ticket_or_404(ticket: DeletionTicket | None, mentor: User) -> DeletionTicket:
    """
    Raises 404 (not 403) when a ticket doesn't exist or doesn't belong to
    this mentor — we reveal nothing about other mentors' tickets.
    """
    if ticket is None or ticket.mentor_id != mentor.id:
        raise HTTPException(status_code=404, detail="Deletion ticket not found")
    return ticket


# ─── student-facing endpoints ────────────────────────────────────────────────

@router.get("/mine/{project_id}", response_model=DeletionTicketResponse)
async def get_my_ticket(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the student's own pending deletion ticket for a given project, or 404.
    Used by the frontend to surface the ticket ID for the Cancel Request button.
    """
    result = await db.execute(
        select(DeletionTicket).where(
            DeletionTicket.project_id == project_id,
            DeletionTicket.student_id == current_user.id,
            DeletionTicket.status == "pending",
        )
    )
    ticket = result.scalars().first()
    if not ticket:
        raise HTTPException(status_code=404, detail="No pending deletion ticket found for this project")
    return ticket


@router.delete("/{ticket_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_my_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Student-only: cancel their own pending deletion ticket.
    - Verifies ticket exists and belongs to the requesting student (not just any student).
    - Verifies ticket is still pending (cannot cancel an already approved/rejected ticket).
    - Deletes the ticket and resets project.status back to 'active'.
    """
    result = await db.execute(
        select(DeletionTicket).where(DeletionTicket.id == ticket_id)
    )
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Deletion ticket not found")

    # Ownership — only the student who created it can cancel it
    if ticket.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel your own deletion requests")

    if ticket.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel a ticket that is already '{ticket.status}'.",
        )

    # Revert project status
    proj_result = await db.execute(
        select(Project).where(Project.id == ticket.project_id)
    )
    project = proj_result.scalars().first()
    if project:
        project.status = "active"

    await db.delete(ticket)
    await db.commit()
    return {"detail": "Deletion request cancelled. Project is active again."}




def _own_ticket_or_404(ticket: DeletionTicket | None, mentor: User) -> DeletionTicket:
    """
    Raises 404 (not 403) when a ticket doesn't exist or doesn't belong to
    this mentor — we reveal nothing about other mentors' tickets.
    """
    if ticket is None or ticket.mentor_id != mentor.id:
        raise HTTPException(status_code=404, detail="Deletion ticket not found")
    return ticket


@router.get("/", response_model=List[DeletionTicketResponse])
async def list_my_tickets(
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """
    Returns only pending deletion tickets assigned to the authenticated mentor.
    Explicitly filtered by ticket.mentor_id == current_user.id server-side.
    """
    result = await db.execute(
        select(DeletionTicket)
        .where(
            DeletionTicket.mentor_id == mentor.id,
            DeletionTicket.status == "pending",
        )
        .order_by(DeletionTicket.created_at.asc())
    )
    return result.scalars().all()


@router.post("/{ticket_id}/approve", response_model=DeletionTicketResponse)
async def approve_ticket(
    ticket_id: str,
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """
    Approve a pending deletion request.
    Permanently deletes the project (CASCADE handles tasks / commits / messages).
    Only the ticket's assigned mentor can approve — other mentors get a 404.
    """
    result = await db.execute(
        select(DeletionTicket).where(DeletionTicket.id == ticket_id)
    )
    ticket = _own_ticket_or_404(result.scalars().first(), mentor)

    if ticket.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Ticket is already '{ticket.status}' — no further action possible.",
        )

    # Mark ticket approved first so we can return it after project deletion
    ticket.status = "approved"

    # Permanently delete the project; CASCADE removes tasks, commits, messages
    proj_result = await db.execute(
        select(Project).where(Project.id == ticket.project_id)
    )
    project = proj_result.scalars().first()
    project_title = project.title if project else ticket.project_id
    if project:
        await db.delete(project)

    # Activity log
    db.add(MentorActivityLog(
        id=str(uuid.uuid4()),
        mentor_id=mentor.id,
        action_type="approved_deletion",
        student_id=ticket.student_id,
        project_id=None,   # project is about to be deleted
        detail=f"Approved deletion of project '{project_title}'",
    ))

    # Notify the student
    db.add(Notification(
        id=str(uuid.uuid4()),
        user_id=ticket.student_id,
        type="deletion_approved",
        message=f"Your deletion request for '{project_title}' has been approved. The project has been permanently deleted.",
        related_project_id=None,
        is_read=False,
    ))

    await db.commit()
    # ticket is detached after commit (project cascade), refresh from id
    result2 = await db.execute(
        select(DeletionTicket).where(DeletionTicket.id == ticket_id)
    )
    refreshed = result2.scalars().first()
    if refreshed is None:
        # Ticket was cascade-deleted with the project; return the in-memory copy
        return ticket
    return refreshed


@router.post("/{ticket_id}/reject", response_model=DeletionTicketResponse)
async def reject_ticket(
    ticket_id: str,
    body: RejectionBody,
    db: AsyncSession = Depends(get_db),
    mentor: User = Depends(get_current_mentor),
):
    """
    Reject a pending deletion request.
    Resets project.status back to 'active' and stores the mentor's rejection note
    on the ticket so the student can read it.
    Only the ticket's assigned mentor can reject — other mentors get a 404.
    """
    result = await db.execute(
        select(DeletionTicket).where(DeletionTicket.id == ticket_id)
    )
    ticket = _own_ticket_or_404(result.scalars().first(), mentor)

    if ticket.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Ticket is already '{ticket.status}' — no further action possible.",
        )

    ticket.status = "rejected"
    ticket.rejection_note = body.rejection_note

    # Restore project status so the student can keep working
    proj_result = await db.execute(
        select(Project).where(Project.id == ticket.project_id)
    )
    project = proj_result.scalars().first()
    if project:
        project.status = "active"

    # Activity log
    db.add(MentorActivityLog(
        id=str(uuid.uuid4()),
        mentor_id=mentor.id,
        action_type="rejected_deletion",
        student_id=ticket.student_id,
        project_id=ticket.project_id,
        detail=body.rejection_note or "No note provided",
    ))

    # Notify the student with the rejection note
    db.add(Notification(
        id=str(uuid.uuid4()),
        user_id=ticket.student_id,
        type="deletion_rejected",
        message=f"Your deletion request was rejected by your mentor. Note: {body.rejection_note or 'No reason given'}",
        related_project_id=ticket.project_id,
        is_read=False,
    ))

    await db.commit()
    await db.refresh(ticket)
    return ticket
