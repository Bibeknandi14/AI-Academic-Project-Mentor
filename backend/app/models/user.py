import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
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
    created_at = Column(DateTime, default=datetime.utcnow)
