"""Quản lý conversation, messages, context."""
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Conversation, Message, MessageRole, ConversationStatus


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(
        self,
        channel_user_id: str,
        channel: str = "messenger",
    ) -> Conversation:
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.channel_user_id == channel_user_id,
                Conversation.channel == channel,
                Conversation.status == ConversationStatus.active,
            )
            .order_by(Conversation.updated_at.desc())
            .limit(1)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            return conversation

        conversation = Conversation(
            channel_user_id=channel_user_id,
            channel=channel,
            context={"intent": None, "step": None, "temp_data": {}},
        )
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def is_message_processed(self, external_id: str) -> bool:
        if not external_id:
            return False
        result = await self.db.execute(
            select(Message.id).where(Message.external_id == external_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def add_message(
        self,
        conversation_id: int,
        role: MessageRole,
        content: str,
        tokens_used: int = 0,
        external_id: Optional[str] = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tokens_used=tokens_used,
            external_id=external_id,
        )
        self.db.add(message)

        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.last_message_at = datetime.utcnow()
            conversation.updated_at = datetime.utcnow()

        await self.db.flush()
        return message

    async def get_claude_messages(
        self, conversation: Conversation, limit: int = 20
    ) -> list[dict]:
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        return [m.to_claude_format() for m in messages if m.role != MessageRole.system]

    async def get_context_summary(self, conversation_id: int) -> str:
        conversation = await self.db.get(Conversation, conversation_id)
        if not conversation or not conversation.context:
            return ""
        ctx = conversation.context
        parts = []
        if ctx.get("intent"):
            parts.append(f"intent={ctx['intent']}")
        if ctx.get("step"):
            parts.append(f"step={ctx['step']}")
        if ctx.get("temp_data"):
            parts.append(f"data={ctx['temp_data']}")
        return "; ".join(parts)

    async def update_context(self, conversation_id: int, patch: dict[str, Any]) -> None:
        conversation = await self.db.get(Conversation, conversation_id)
        if not conversation:
            return
        current = dict(conversation.context or {})
        for key, value in patch.items():
            if key == "temp_data" and isinstance(value, dict):
                current["temp_data"] = {**current.get("temp_data", {}), **value}
            else:
                current[key] = value
        conversation.context = current
        conversation.updated_at = datetime.utcnow()
        await self.db.flush()

    async def set_pending_booking(
        self, conversation_id: int, booking_id: int, guest_id: Optional[int] = None
    ) -> None:
        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.pending_booking_id = booking_id
            if guest_id:
                conversation.guest_id = guest_id
            await self.db.flush()

    async def mark_waiting_human(self, conversation_id: int) -> None:
        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.status = ConversationStatus.waiting_human
            await self.db.flush()

    async def resolve(self, conversation_id: int) -> Optional[Conversation]:
        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.status = ConversationStatus.resolved
            await self.db.flush()
        return conversation

    async def reopen(self, conversation_id: int) -> Optional[Conversation]:
        conversation = await self.db.get(Conversation, conversation_id)
        if conversation:
            conversation.status = ConversationStatus.active
            await self.db.flush()
        return conversation

    async def list_conversations(
        self,
        status: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[Conversation, int]]:
        stmt = (
            select(Conversation, func.count(Message.id).label("message_count"))
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .group_by(Conversation.id)
            .order_by(Conversation.last_message_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if status:
            stmt = stmt.where(Conversation.status == ConversationStatus(status))
        if channel:
            stmt = stmt.where(Conversation.channel == channel)
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def get_detail(self, conversation_id: int) -> Optional[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()
