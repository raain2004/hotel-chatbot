"""Thông báo nội bộ + webhook tùy chọn."""
import logging
from typing import Optional

import httpx
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Notification, NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        type: NotificationType,
        title: str,
        message: str,
        booking_id: Optional[int] = None,
        conversation_id: Optional[int] = None,
    ) -> Notification:
        notification = Notification(
            type=type,
            title=title,
            message=message,
            booking_id=booking_id,
            conversation_id=conversation_id,
        )
        self.db.add(notification)
        await self.db.flush()
        await self._push_webhook(title, message)
        return notification

    async def notify_new_booking(
        self, booking_code: str, guest_name: str, booking_id: int
    ) -> Notification:
        return await self.create(
            NotificationType.new_booking,
            f"Đặt phòng mới: {booking_code}",
            f"Khách {guest_name} vừa đặt phòng qua chatbot.",
            booking_id=booking_id,
        )

    async def notify_human_handoff(
        self, channel_user_id: str, conversation_id: int
    ) -> Notification:
        return await self.create(
            NotificationType.human_handoff,
            "Khách cần gặp nhân viên",
            f"PSID/kênh: {channel_user_id} — cần hỗ trợ thủ công.",
            conversation_id=conversation_id,
        )

    async def notify_booking_cancelled(
        self, booking_code: str, booking_id: int
    ) -> Notification:
        return await self.create(
            NotificationType.booking_cancelled,
            f"Đã hủy: {booking_code}",
            f"Booking {booking_code} đã được hủy.",
            booking_id=booking_id,
        )

    async def list_notifications(
        self, unread_only: bool = False, limit: int = 50
    ) -> list[Notification]:
        stmt = select(Notification).order_by(Notification.created_at.desc()).limit(limit)
        if unread_only:
            stmt = stmt.where(Notification.is_read == False)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_read(self, notification_id: int) -> Optional[Notification]:
        notification = await self.db.get(Notification, notification_id)
        if notification:
            notification.is_read = True
            await self.db.flush()
        return notification

    async def mark_all_read(self) -> int:
        result = await self.db.execute(
            update(Notification)
            .where(Notification.is_read == False)
            .values(is_read=True)
        )
        return result.rowcount

    async def count_unread(self) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(Notification.is_read == False)
        )
        return result.scalar() or 0

    async def _push_webhook(self, title: str, message: str) -> None:
        if not settings.notify_webhook_url:
            return
        payload = {"text": f"*{title}*\n{message}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(settings.notify_webhook_url, json=payload)
        except Exception:
            logger.exception("Gửi notify webhook thất bại")
