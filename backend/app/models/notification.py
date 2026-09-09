from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from app.db.session import Base


class Notification(Base):
    """
    Simple in-app notification row.  Written at event points (deletion request,
    approve/reject, supervision message).  Never mutated except to mark is_read.
    """
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, index=True)
    # The user who should receive and see this notification
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String, nullable=False)
    # Human-readable message displayed in the bell dropdown
    message = Column(String, nullable=False)
    # Optional link-back for navigating to the right tab
    related_project_id = Column(String, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
