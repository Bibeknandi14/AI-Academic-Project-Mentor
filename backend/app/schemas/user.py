import random
import string
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


def generate_mentor_code() -> str:
    """
    Generate a collision-resistant mentor code in the format MNT-XXXXX
    where XXXXX is 5 uppercase alphanumeric characters (A-Z, 0-9).
    Example: MNT-7K92P
    """
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=5))
    return f"MNT-{suffix}"


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.STUDENT
    github_username: Optional[str] = None
    assigned_mentor_id: Optional[str] = None


class UserCreate(UserBase):
    password: str
    # Optional: students may supply their mentor's code at registration time.
    # Resolved server-side → assigned_mentor_id. Not stored directly.
    mentor_code: Optional[str] = None


class AssignedMentorInfo(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    mentor_code: Optional[str] = None

    model_config = {"from_attributes": True}


class UserSelfUpdate(BaseModel):
    """Fields allowed to be self-updated by the authenticated user via PATCH /api/auth/me."""
    full_name: Optional[str] = None
    github_username: Optional[str] = None


class UserUpdate(BaseModel):
    """Partial update — used from dashboards (e.g. student linking to a mentor)."""
    full_name: Optional[str] = None
    github_username: Optional[str] = None
    assigned_mentor_id: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: str
    # Present only for MENTOR accounts; null for students.
    mentor_code: Optional[str] = None
    created_at: datetime
    # Present for students if linked to a mentor
    assigned_mentor: Optional[AssignedMentorInfo] = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

