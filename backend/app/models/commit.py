from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from app.db.session import Base

class CommitLog(Base):
    __tablename__ = "commit_logs"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    commit_hash = Column(String, nullable=False, index=True)
    author_name = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    commit_date = Column(DateTime, default=datetime.utcnow)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
