"""Thống kê và dữ liệu dashboard."""
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Booking,
    BookingStatus,
    Conversation,
    ConversationStatus,
    Guest,
)
from app.schemas.dashboard import DashboardStats, RecentBookingOut
from app.services.notification_service import NotificationService


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notifications = NotificationService(db)

    async def get_stats(self) -> DashboardStats:
        total = await self._count_bookings()
        pending = await self._count_bookings(BookingStatus.pending)
        confirmed = await self._count_bookings(BookingStatus.confirmed)
        active_conv = await self._count_conversations(ConversationStatus.active)
        waiting = await self._count_conversations(ConversationStatus.waiting_human)
        unread = await self.notifications.count_unread()

        revenue_result = await self.db.execute(
            select(func.coalesce(func.sum(Booking.total_amount), 0)).where(
                Booking.status.in_(
                    [BookingStatus.confirmed, BookingStatus.checked_in, BookingStatus.checked_out]
                )
            )
        )
        revenue = revenue_result.scalar() or Decimal("0")

        return DashboardStats(
            total_bookings=total,
            pending_bookings=pending,
            confirmed_bookings=confirmed,
            active_conversations=active_conv,
            waiting_human_conversations=waiting,
            unread_notifications=unread,
            total_revenue=Decimal(str(revenue)),
        )

    async def get_recent_bookings(self, limit: int = 10) -> list[RecentBookingOut]:
        result = await self.db.execute(
            select(Booking)
            .options(selectinload(Booking.guest))
            .order_by(Booking.created_at.desc())
            .limit(limit)
        )
        bookings = result.scalars().all()
        return [
            RecentBookingOut(
                id=b.id,
                booking_code=b.booking_code,
                guest_name=b.guest.full_name if b.guest else "—",
                check_in_date=b.check_in_date,
                check_out_date=b.check_out_date,
                status=b.status.value,
                total_amount=b.total_amount,
                created_at=b.created_at,
            )
            for b in bookings
        ]

    async def _count_bookings(self, status: BookingStatus | None = None) -> int:
        stmt = select(func.count()).select_from(Booking)
        if status:
            stmt = stmt.where(Booking.status == status)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _count_conversations(self, status: ConversationStatus) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.status == status)
        )
        return result.scalar() or 0
