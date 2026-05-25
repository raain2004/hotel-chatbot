from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import verify_admin_key
from app.database import get_db
from app.models import ConversationStatus
from app.schemas.conversation import (
    ConversationContextUpdate,
    ConversationDetail,
    ConversationOut,
    ConversationStatusUpdate,
    MessageOut,
)
from app.services.conversation_service import ConversationService

router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _to_out(conv, message_count: int = 0) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        channel_user_id=conv.channel_user_id,
        channel=conv.channel,
        status=conv.status.value,
        context=conv.context or {},
        guest_id=conv.guest_id,
        pending_booking_id=conv.pending_booking_id,
        last_message_at=conv.last_message_at,
        created_at=conv.created_at,
        message_count=message_count,
    )


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    status: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    rows = await service.list_conversations(status=status, channel=channel, limit=limit, offset=offset)
    return [_to_out(conv, count) for conv, count in rows]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    conv = await service.get_detail(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
    return ConversationDetail(
        **_to_out(conv, len(conv.messages)).model_dump(),
        messages=[MessageOut.model_validate(m) for m in conv.messages],
    )


@router.patch("/{conversation_id}/context", response_model=ConversationOut)
async def update_context(
    conversation_id: int,
    body: ConversationContextUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    conv = await service.get_detail(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
    await service.update_context(conversation_id, body.context)
    await db.refresh(conv)
    return _to_out(conv)


@router.patch("/{conversation_id}/status", response_model=ConversationOut)
async def update_status(
    conversation_id: int,
    body: ConversationStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = ConversationService(db)
    if body.status == "resolved":
        conv = await service.resolve(conversation_id)
    elif body.status == "active":
        conv = await service.reopen(conversation_id)
    elif body.status == "waiting_human":
        conv = await service.get_detail(conversation_id)
        if conv:
            await service.mark_waiting_human(conversation_id)
            conv = await service.get_detail(conversation_id)
    else:
        conv = None

    if not conv:
        raise HTTPException(status_code=404, detail="Không tìm thấy conversation")
    return _to_out(conv)
