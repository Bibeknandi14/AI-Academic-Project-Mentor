import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, Token, UserLogin, generate_mentor_code

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Duplicate email check
    result = await db.execute(select(User).where(User.email == user_in.email))
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
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
        github_username=user_in.github_username,
        mentor_code=mentor_code,
        assigned_mentor_id=assigned_mentor_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(subject=user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
