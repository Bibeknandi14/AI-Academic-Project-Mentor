from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from app.db.session import Base


class SupervisorMessage(Base):
    """
    Human mentor ↔ student direct messaging within a project context.

    This table is intentionally separate from ChatMessage (app/models/chat.py),
    which stores AI-mentor Q&A interactions.  SupervisorMessage is for
    human-to-human supervision communication only.
    """
    __tablename__ = "supervisor_messages"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(
        String, ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    # Either the mentor or the student may be the sender
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
