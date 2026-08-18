from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.commit import CommitLog
from app.services.github_service import GitHubService

router = APIRouter(prefix="/github", tags=["GitHub Tracking"])

@router.post("/sync/{project_id}")
async def sync_github_commits(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await GitHubService.sync_project_commits(db, project_id)
    return result

@router.get("/commits/{project_id}")
async def get_project_commits(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(CommitLog)
        .where(CommitLog.project_id == project_id)
        .order_by(CommitLog.commit_date.desc())
    )
    commits = result.scalars().all()
    return commits
