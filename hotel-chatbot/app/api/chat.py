from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.claude_service import ClaudeService, ClaudeServiceError

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Endpoint test chatbot (không qua Messenger)."""
    service = ClaudeService(db)
    try:
        return await service.process_message(
            channel_user_id=body.user_id,
            message=body.message,
            channel=body.channel,
        )
    except ClaudeServiceError as e:
        raise HTTPException(status_code=503, detail=e.message)
