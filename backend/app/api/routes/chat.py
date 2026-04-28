"""
Role-aware chat endpoint.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.chat_service import answer_query

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=2)


@router.post("")
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await answer_query(
        db,
        query=data.query,
        role=current_user.role,
        user_id=current_user.id,
        ngo_id=current_user.ngo_id,
    )
