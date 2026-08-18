from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON
from app.db.session import Base

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    sender = Column(String, nullable=False) # "USER" or "AI"
    message = Column(Text, nullable=False)
    context_used = Column(JSON, nullable=True) # stores injected task/commit metadata
    created_at = Column(DateTime, default=datetime.utcnow)
