from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint
from app.db.session import Base


class DeletionTicket(Base):
    """
    Represents a student's request to delete a project.

    Lifecycle:
        student submits → status="pending"
        mentor approves → status="approved"  (project.status → "pending_deletion")
        mentor rejects  → status="rejected"

    Only one open (pending) ticket per project is expected at a time;
    enforcement is left to the API layer.
    """
    __tablename__ = "deletion_tickets"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_deletion_ticket_status"
        ),
    )

    id = Column(String, primary_key=True, index=True)
    project_id = Column(
        String, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    # The student who raised the request
    student_id = Column(String, ForeignKey("users.id"), nullable=False)
    # The mentor who will approve / reject
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending", index=True)
    # Populated by the mentor when rejecting; null until then.
    rejection_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
