from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from app.db.session import Base


class MentorActivityLog(Base):
    """
    Unified audit trail for every significant mentor action.
    Written at each event point (approve, reject, mark_complete, unassign).
    Never modified after creation — append-only.
    """
    __tablename__ = "mentor_activity_logs"

    id = Column(String, primary_key=True, index=True)
    mentor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(
        String, nullable=False,
        # "approved_deletion" | "rejected_deletion" | "marked_completed" | "unassigned_student"
    )
    student_id = Column(String, ForeignKey("users.id"), nullable=True)
    project_id = Column(
        String, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
