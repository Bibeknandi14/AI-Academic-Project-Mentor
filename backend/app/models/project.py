from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint
from app.db.session import Base

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'pending_deletion', 'completed')",
            name="ck_project_status"
        ),
    )

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    github_repo = Column(String, nullable=True)  # e.g. "owner/repo"
    mentor_id = Column(String, ForeignKey("users.id"), nullable=True)
    # Lifecycle status: "active" | "pending_deletion" | "completed"
    status = Column(String, nullable=False, default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProjectMember(Base):
    __tablename__ = "project_members"

    id = Column(String, primary_key=True, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, default="MEMBER")
    created_at = Column(DateTime, default=datetime.utcnow)
