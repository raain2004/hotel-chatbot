from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AvailabilityQuery(BaseModel):
    check_in: date
    check_out: date
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    room_type_id: Optional[int] = None
    hotel_id: Optional[int] = None

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info):
        check_in = info.data.get("check_in")
        if check_in and v <= check_in:
            raise ValueError("check_out phải sau check_in")
        return v


class AvailableRoomType(BaseModel):
    room_type_id: int
    name: str
    description: Optional[str] = None
    price_per_night: Decimal
    available_rooms: int
    max_adults: int
    max_children: int


class AvailabilityResponse(BaseModel):
    check_in: date
    check_out: date
    num_nights: int
    available: bool
    room_types: list[AvailableRoomType]


class BookingCreate(BaseModel):
    guest_name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=8, max_length=20)
    check_in: date
    check_out: date
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    room_type_id: int
    hotel_id: Optional[int] = None
    special_requests: Optional[str] = None
    messenger_id: Optional[str] = None
    email: Optional[str] = None
    source: str = "chatbot"

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info):
        check_in = info.data.get("check_in")
        if check_in and v <= check_in:
            raise ValueError("check_out phải sau check_in")
        return v


class GuestBrief(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None

    model_config = {"from_attributes": True}


class BookingResponse(BaseModel):
    id: int
    booking_code: str
    hotel_id: int
    room_id: Optional[int] = None
    check_in_date: date
    check_out_date: date
    num_nights: int
    num_adults: int
    num_children: int
    status: str
    payment_status: str
    total_amount: Decimal
    special_requests: Optional[str] = None
    source: str
    guest: GuestBrief
    created_at: datetime

    model_config = {"from_attributes": True}
