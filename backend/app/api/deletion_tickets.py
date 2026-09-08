"""
Deletion ticket management — mentor-facing endpoints.

Access control is enforced at every query:
  • GET  /deletion-tickets/          → only tickets where ticket.mentor_id == current_mentor.id
  • POST /deletion-tickets/{id}/approve → same ownership check (404 if not theirs)
  • POST /deletion-tickets/{id}/reject  → same ownership check + rejection note stored

A mentor CANNOT see or act on another mentor's tickets under any circumstance.
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_mentor
from app.models.user import User
from app.models.project import Project
from app.models.deletion_ticket import DeletionTicket
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
    if project:
        await db.delete(project)

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

    await db.commit()
    await db.refresh(ticket)
    return ticket
