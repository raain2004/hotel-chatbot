import pytest

from app.models import MessageRole
from app.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_message_dedup(db_session):
    svc = ConversationService(db_session)
    conv = await svc.get_or_create("u1", "web")
    await svc.add_message(conv.id, MessageRole.user, "hi", external_id="mid-1")
    assert await svc.is_message_processed("mid-1") is True
    assert await svc.is_message_processed("mid-2") is False


@pytest.mark.asyncio
async def test_context_update(db_session):
    svc = ConversationService(db_session)
    conv = await svc.get_or_create("u2", "web")
    await svc.update_context(conv.id, {"intent": "booking", "step": "dates"})
    await db_session.refresh(conv)
    assert conv.context["intent"] == "booking"
