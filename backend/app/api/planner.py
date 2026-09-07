from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.planner import RoadmapGenerationInput, RoadmapGenerationOutput
from app.services.planner_service import PlannerService

router = APIRouter(prefix="/planner", tags=["AI Roadmap Planner"])

@router.post("/generate", response_model=RoadmapGenerationOutput)
async def generate_roadmap(
    input_data: RoadmapGenerationInput,
    current_user: User = Depends(get_current_user)
):
    return await PlannerService.generate_roadmap(input_data=input_data, current_user=current_user)

@router.post("/convert-to-project", status_code=status.HTTP_201_CREATED)
async def convert_roadmap_to_project(
    roadmap_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await PlannerService.convert_to_project(
        roadmap_data=roadmap_data,
        db=db,
        current_user=current_user
    )
