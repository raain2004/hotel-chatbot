"""Thông báo nội bộ cho nhân viên (dashboard)."""
from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationType(enum.Enum):
    new_booking = "new_booking"
    human_handoff = "human_handoff"
    booking_cancelled = "booking_cancelled"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    booking_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("bookings.id"))
    conversation_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("conversations.id")
    )
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
