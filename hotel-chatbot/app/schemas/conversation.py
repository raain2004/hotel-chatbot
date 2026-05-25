from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    external_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: int
    channel_user_id: str
    channel: str
    status: str
    context: dict[str, Any] = Field(default_factory=dict)
    guest_id: Optional[int] = None
    pending_booking_id: Optional[int] = None
    last_message_at: datetime
    created_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = Field(default_factory=list)


class ConversationContextUpdate(BaseModel):
    context: dict[str, Any]


class ConversationStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|resolved|waiting_human)$")
