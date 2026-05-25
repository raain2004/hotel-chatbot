"""
Models: Hotel, RoomType, Room
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Integer, Numeric, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base


class RoomStatus(enum.Enum):
    available = "available"
    occupied = "occupied"
    maintenance = "maintenance"
    cleaning = "cleaning"


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    check_in_time: Mapped[str] = mapped_column(String(10), default="14:00")
    check_out_time: Mapped[str] = mapped_column(String(10), default="12:00")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    room_types: Mapped[list["RoomType"]] = relationship("RoomType", back_populates="hotel")
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="hotel")

    def __repr__(self):
        return f"<Hotel {self.name}>"


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hotel_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotels.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # VD: "Superior", "Deluxe", "Suite"
    description: Mapped[Optional[str]] = mapped_column(Text)
    price_per_night: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    max_adults: Mapped[int] = mapped_column(Integer, default=2)
    max_children: Mapped[int] = mapped_column(Integer, default=1)
    amenities: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    hotel: Mapped["Hotel"] = relationship("Hotel", back_populates="room_types")
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="room_type")

    def __repr__(self):
        return f"<RoomType {self.name} - {self.price_per_night}>"


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    hotel_id: Mapped[int] = mapped_column(Integer, ForeignKey("hotels.id"), nullable=False)
    room_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("room_types.id"), nullable=False)
    room_number: Mapped[str] = mapped_column(String(20), nullable=False)  # VD: "101", "205A"
    floor: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[RoomStatus] = mapped_column(
        Enum(RoomStatus), default=RoomStatus.available
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    hotel: Mapped["Hotel"] = relationship("Hotel", back_populates="rooms")
    room_type: Mapped["RoomType"] = relationship("RoomType", back_populates="rooms")

    def __repr__(self):
        return f"<Room {self.room_number} - {self.status.value}>"
