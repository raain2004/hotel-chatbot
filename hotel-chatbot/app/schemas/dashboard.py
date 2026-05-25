from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_bookings: int
    pending_bookings: int
    confirmed_bookings: int
    active_conversations: int
    waiting_human_conversations: int
    unread_notifications: int
    total_revenue: Decimal


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    booking_id: Optional[int] = None
    conversation_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RecentBookingOut(BaseModel):
    id: int
    booking_code: str
    guest_name: str
    check_in_date: date
    check_out_date: date
    status: str
    total_amount: Decimal
    created_at: datetime
