from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.chat import ChatMessage
from app.schemas.mentorship import MentorshipQueryInput, ChatMessageResponse
from app.services.mentorship_service import MentorshipService

router = APIRouter(prefix="/mentorship", tags=["AI Mentorship Chat"])

@router.post("/chat", response_model=ChatMessageResponse)
async def ask_mentorship_ai(
    query_in: MentorshipQueryInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    response = await MentorshipService.process_student_query(
        db=db,
        user_id=current_user.id,
        query_input=query_in
    )
    return response

@router.get("/history/{project_id}", response_model=List[ChatMessageResponse])
async def get_chat_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.project_id == project_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()
    return messages
