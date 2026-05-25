"""
Models: Conversation, Message
Lưu lịch sử chat để Claude có context giữa các lần nhắn tin.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class ConversationStatus(enum.Enum):
    active = "active"
    resolved = "resolved"
    waiting_human = "waiting_human"  # Chuyển sang nhân viên


class MessageRole(enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # ID từ kênh chat (Messenger PSID, Zalo User ID, ...)
    channel_user_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), default="messenger")  # messenger, zalo, web
    guest_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("guests.id"))

    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.active
    )

    # Context hiện tại của cuộc trò chuyện (dùng cho Claude)
    # VD: {"intent": "booking", "step": "collect_dates", "temp_data": {...}}
    context: Mapped[dict] = mapped_column(JSON, default=dict)

    # Booking đang được xử lý trong conversation này
    pending_booking_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bookings.id")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_message_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", order_by="Message.created_at"
    )

    def __repr__(self):
        return f"<Conversation {self.channel}/{self.channel_user_id}>"

    def get_recent_messages(self, limit: int = 20) -> list["Message"]:
        """Lấy N tin nhắn gần nhất để đưa vào context Claude."""
        return self.messages[-limit:]


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("conversations.id"), nullable=False, index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata
    is_error: Mapped[bool] = mapped_column(Boolean, default=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    # Messenger mid — chống xử lý trùng khi Meta retry webhook
    external_id: Mapped[Optional[str]] = mapped_column(String(200), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.role.value}: {self.content[:50]}>"

    def to_claude_format(self) -> dict:
        """Chuyển sang format messages[] của Claude API."""
        return {
            "role": self.role.value,
            "content": self.content,
        }
