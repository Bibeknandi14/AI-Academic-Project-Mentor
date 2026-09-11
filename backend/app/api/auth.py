import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserResponse,
    Token,
    UserLogin,
    UserSelfUpdate,
    AssignedMentorInfo,
    generate_mentor_code,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    clean_email = user_in.email.strip().lower()
    # Duplicate email check (case-insensitive)
    result = await db.execute(select(User).where(func.lower(User.email) == clean_email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email is already registered")

    mentor_code = None
    assigned_mentor_id = None

    if user_in.role == UserRole.MENTOR:
        # Generate a collision-resistant mentor code; retry up to 10 times on collision.
        for _ in range(10):
            candidate = generate_mentor_code()
            taken = await db.execute(select(User).where(User.mentor_code == candidate))
            if not taken.scalars().first():
                mentor_code = candidate
                break
        if mentor_code is None:
            raise HTTPException(status_code=500, detail="Could not generate a unique mentor code. Please try again.")

    elif user_in.role == UserRole.STUDENT and user_in.mentor_code:
        # Validate the supplied mentor code and resolve → mentor's user id.
        mentor_result = await db.execute(
            select(User).where(
                User.mentor_code == user_in.mentor_code.strip().upper(),
                User.role == UserRole.MENTOR,
            )
        )
        mentor = mentor_result.scalars().first()
        if not mentor:
            raise HTTPException(
                status_code=400,
                detail=f"Mentor code '{user_in.mentor_code}' is invalid or does not belong to any mentor."
            )
        assigned_mentor_id = mentor.id

    user = User(
        id=str(uuid.uuid4()),
        email=clean_email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name.strip(),
        role=user_in.role,
        github_username=user_in.github_username.strip() if user_in.github_username else None,
        mentor_code=mentor_code,
        assigned_mentor_id=assigned_mentor_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    clean_username = form_data.username.strip().lower()
    result = await db.execute(select(User).where(func.lower(User.email) == clean_username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user has an assigned mentor to return in login response
    assigned_mentor = None
    if user.assigned_mentor_id:
        mentor_result = await db.execute(select(User).where(User.id == user.assigned_mentor_id))
        mentor = mentor_result.scalars().first()
        if mentor:
            assigned_mentor = AssignedMentorInfo(
                id=mentor.id,
                full_name=mentor.full_name,
                email=mentor.email,
                mentor_code=mentor.mentor_code,
            )

    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        github_username=user.github_username,
        assigned_mentor_id=user.assigned_mentor_id,
        mentor_code=user.mentor_code,
        created_at=user.created_at,
        assigned_mentor=assigned_mentor,
    )

    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_resp
    }

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    assigned_mentor = None
    if current_user.assigned_mentor_id:
        mentor_result = await db.execute(
            select(User).where(User.id == current_user.assigned_mentor_id)
        )
        mentor = mentor_result.scalars().first()
        if mentor:
            assigned_mentor = AssignedMentorInfo(
                id=mentor.id,
                full_name=mentor.full_name,
                email=mentor.email,
                mentor_code=mentor.mentor_code,
            )

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        github_username=current_user.github_username,
        assigned_mentor_id=current_user.assigned_mentor_id,
        mentor_code=current_user.mentor_code,
        created_at=current_user.created_at,
        assigned_mentor=assigned_mentor,
    )

@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_in: UserSelfUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Allows the logged-in user to update their own full_name and github_username.
    Email, role, and mentor_code are protected and cannot be changed here.
    """
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.full_name is not None:
        clean_name = user_in.full_name.strip()
        if not clean_name:
            raise HTTPException(status_code=400, detail="Full name cannot be empty")
        user.full_name = clean_name

    if user_in.github_username is not None:
        clean_gh = user_in.github_username.strip()
        user.github_username = clean_gh if clean_gh else None

    await db.commit()
    await db.refresh(user)

    assigned_mentor = None
    if user.assigned_mentor_id:
        mentor_result = await db.execute(
            select(User).where(User.id == user.assigned_mentor_id)
        )
        mentor = mentor_result.scalars().first()
        if mentor:
            assigned_mentor = AssignedMentorInfo(
                id=mentor.id,
                full_name=mentor.full_name,
                email=mentor.email,
                mentor_code=mentor.mentor_code,
            )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        github_username=user.github_username,
        assigned_mentor_id=user.assigned_mentor_id,
        mentor_code=user.mentor_code,
        created_at=user.created_at,
        assigned_mentor=assigned_mentor,
    )

