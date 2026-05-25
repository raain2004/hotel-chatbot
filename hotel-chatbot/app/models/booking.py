"""
Models: Guest, Booking, BookingRoom
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, Date, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class BookingStatus(enum.Enum):
    pending = "pending"           # Đang chờ xác nhận
    confirmed = "confirmed"       # Đã xác nhận
    checked_in = "checked_in"     # Đã check-in
    checked_out = "checked_out"   # Đã check-out
    cancelled = "cancelled"       # Đã hủy
    no_show = "no_show"          # Không đến


class PaymentStatus(enum.Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"
    refunded = "refunded"


class Guest(Base):
    __tablename__ = "guests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    id_number: Mapped[Optional[str]] = mapped_column(String(50))
    nationality: Mapped[Optional[str]] = mapped_column(String(100), default="Vietnam")
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date)
    messenger_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, unique=True)
    zalo_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="guest")

    def __repr__(self):
        return f"<Guest {self.full_name}>"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    booking_code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    guest_id: Mapped[int] = mapped_column(Integer, ForeignKey("guests.id"), nullable=False)
    hotel_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotels.id"), nullable=False)
    room_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rooms.id"))

    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    num_adults: Mapped[int] = mapped_column(Integer, default=1)
    num_children: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.pending
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.unpaid
    )

    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    special_requests: Mapped[Optional[str]] = mapped_column(Text)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Nguồn đặt phòng
    source: Mapped[str] = mapped_column(String(50), default="chatbot")  # chatbot, walk-in, phone, ota

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    checked_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    guest: Mapped["Guest"] = relationship("Guest", back_populates="bookings")

    def __repr__(self):
        return f"<Booking {self.booking_code} - {self.status.value}>"

    @property
    def num_nights(self) -> int:
        return (self.check_out_date - self.check_in_date).days
