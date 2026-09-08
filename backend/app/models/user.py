import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from app.db.session import Base

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    MENTOR = "MENTOR"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    github_username = Column(String, nullable=True)
    # Populated at registration for MENTOR accounts only; null for students.
    # Format: "MNT-XXXXX" (uppercase alphanumeric, collision-resistant).
    mentor_code = Column(String, unique=True, nullable=True, index=True)
    # FK to the mentor this student is assigned to; null until explicitly linked.
    assigned_mentor_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
