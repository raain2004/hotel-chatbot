"""Logic đặt phòng, kiểm tra phòng trống, tra cứu booking."""
import random
import string
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Hotel,
    Room,
    RoomType,
    RoomStatus,
    Guest,
    Booking,
    BookingStatus,
)
from app.schemas.booking import (
    AvailabilityQuery,
    AvailabilityResponse,
    AvailableRoomType,
    BookingCreate,
    BookingResponse,
)

ACTIVE_BOOKING_STATUSES = (
    BookingStatus.pending,
    BookingStatus.confirmed,
    BookingStatus.checked_in,
)


class BookingServiceError(Exception):
    def __init__(self, message: str, code: str = "booking_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_default_hotel(self) -> Optional[Hotel]:
        result = await self.db.execute(
            select(Hotel).where(Hotel.is_active == True).order_by(Hotel.id).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_hotel_dict(self, hotel_id: Optional[int] = None) -> dict:
        hotel = await self._get_hotel(hotel_id)
        if not hotel:
            return {}
        return {
            "id": hotel.id,
            "name": hotel.name,
            "address": hotel.address,
            "phone": hotel.phone,
            "check_in_time": hotel.check_in_time,
            "check_out_time": hotel.check_out_time,
        }

    async def get_room_types_dict(self, hotel_id: Optional[int] = None) -> list[dict]:
        hotel = await self._get_hotel(hotel_id)
        if not hotel:
            return []

        result = await self.db.execute(
            select(RoomType)
            .where(RoomType.hotel_id == hotel.id, RoomType.is_active == True)
            .order_by(RoomType.price_per_night)
        )
        room_types = result.scalars().all()
        return [
            {
                "id": rt.id,
                "name": rt.name,
                "description": rt.description or "",
                "price_per_night": float(rt.price_per_night),
                "max_adults": rt.max_adults,
                "max_children": rt.max_children,
            }
            for rt in room_types
        ]

    async def check_availability(self, query: AvailabilityQuery) -> AvailabilityResponse:
        hotel = await self._get_hotel(query.hotel_id)
        if not hotel:
            raise BookingServiceError("Không tìm thấy khách sạn", "hotel_not_found")

        num_nights = (query.check_out - query.check_in).days
        booked_room_ids = await self._get_booked_room_ids(query.check_in, query.check_out)

        stmt = (
            select(Room, RoomType)
            .join(RoomType, Room.room_type_id == RoomType.id)
            .where(
                Room.hotel_id == hotel.id,
                Room.status == RoomStatus.available,
                RoomType.is_active == True,
                RoomType.max_adults >= query.adults,
            )
        )
        if query.room_type_id:
            stmt = stmt.where(Room.room_type_id == query.room_type_id)
        if booked_room_ids:
            stmt = stmt.where(Room.id.notin_(booked_room_ids))

        result = await self.db.execute(stmt)
        rows = result.all()

        counts: dict[int, AvailableRoomType] = {}
        for room, room_type in rows:
            if room_type.id not in counts:
                counts[room_type.id] = AvailableRoomType(
                    room_type_id=room_type.id,
                    name=room_type.name,
                    description=room_type.description,
                    price_per_night=room_type.price_per_night,
                    available_rooms=0,
                    max_adults=room_type.max_adults,
                    max_children=room_type.max_children,
                )
            counts[room_type.id].available_rooms += 1

        room_types = list(counts.values())
        return AvailabilityResponse(
            check_in=query.check_in,
            check_out=query.check_out,
            num_nights=num_nights,
            available=len(room_types) > 0,
            room_types=room_types,
        )

    async def create_booking(self, data: BookingCreate) -> BookingResponse:
        hotel = await self._get_hotel(data.hotel_id)
        if not hotel:
            raise BookingServiceError("Không tìm thấy khách sạn", "hotel_not_found")

        availability = await self.check_availability(
            AvailabilityQuery(
                check_in=data.check_in,
                check_out=data.check_out,
                adults=data.adults,
                children=data.children,
                room_type_id=data.room_type_id,
                hotel_id=hotel.id,
            )
        )
        if not availability.available:
            raise BookingServiceError(
                "Không còn phòng trống cho loại phòng và ngày đã chọn",
                "no_availability",
            )

        room = await self._pick_room(
            hotel.id, data.room_type_id, data.check_in, data.check_out
        )
        if not room:
            raise BookingServiceError("Không thể gán phòng", "room_unavailable")

        room_type = await self.db.get(RoomType, data.room_type_id)
        num_nights = (data.check_out - data.check_in).days
        total = room_type.price_per_night * num_nights

        guest = await self._get_or_create_guest(
            full_name=data.guest_name,
            phone=data.phone,
            email=data.email,
            messenger_id=data.messenger_id,
        )

        booking = Booking(
            booking_code=self._generate_booking_code(),
            guest_id=guest.id,
            hotel_id=hotel.id,
            room_id=room.id,
            check_in_date=data.check_in,
            check_out_date=data.check_out,
            num_adults=data.adults,
            num_children=data.children,
            status=BookingStatus.pending,
            total_amount=total,
            special_requests=data.special_requests,
            source=data.source,
        )
        self.db.add(booking)
        await self.db.flush()
        await self.db.refresh(booking, ["guest"])

        from app.services.notification_service import NotificationService

        await NotificationService(self.db).notify_new_booking(
            booking.booking_code, guest.full_name, booking.id
        )

        return self._to_booking_response(booking)

    async def get_booking_by_code(self, booking_code: str) -> Optional[BookingResponse]:
        result = await self.db.execute(
            select(Booking)
            .options(selectinload(Booking.guest))
            .where(Booking.booking_code == booking_code.upper())
        )
        booking = result.scalar_one_or_none()
        if not booking:
            return None
        return self._to_booking_response(booking)

    async def get_bookings_by_phone(self, phone: str) -> list[BookingResponse]:
        result = await self.db.execute(
            select(Booking)
            .join(Guest, Booking.guest_id == Guest.id)
            .options(selectinload(Booking.guest))
            .where(Guest.phone == phone)
            .order_by(Booking.created_at.desc())
        )
        bookings = result.scalars().all()
        return [self._to_booking_response(b) for b in bookings]

    async def cancel_booking(self, booking_code: str) -> BookingResponse:
        result = await self.db.execute(
            select(Booking)
            .options(selectinload(Booking.guest))
            .where(Booking.booking_code == booking_code.upper())
        )
        booking = result.scalar_one_or_none()
        if not booking:
            raise BookingServiceError("Không tìm thấy booking", "not_found")

        if booking.status in (BookingStatus.checked_in, BookingStatus.checked_out):
            raise BookingServiceError(
                "Không thể hủy booking đã check-in/check-out", "invalid_status"
            )

        booking.status = BookingStatus.cancelled
        await self.db.flush()

        from app.services.notification_service import NotificationService

        await NotificationService(self.db).notify_booking_cancelled(
            booking.booking_code, booking.id
        )

        return self._to_booking_response(booking)

    async def confirm_booking(self, booking_code: str) -> BookingResponse:
        result = await self.db.execute(
            select(Booking)
            .options(selectinload(Booking.guest))
            .where(Booking.booking_code == booking_code.upper())
        )
        booking = result.scalar_one_or_none()
        if not booking:
            raise BookingServiceError("Không tìm thấy booking", "not_found")

        booking.status = BookingStatus.confirmed
        booking.confirmed_at = datetime.utcnow()
        await self.db.flush()
        return self._to_booking_response(booking)

    # --- helpers ---

    async def _get_hotel(self, hotel_id: Optional[int] = None) -> Optional[Hotel]:
        if hotel_id:
            return await self.db.get(Hotel, hotel_id)
        return await self.get_default_hotel()

    async def _get_booked_room_ids(self, check_in: date, check_out: date) -> set[int]:
        result = await self.db.execute(
            select(Booking.room_id).where(
                Booking.room_id.isnot(None),
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
                Booking.check_in_date < check_out,
                Booking.check_out_date > check_in,
            )
        )
        return {rid for rid in result.scalars().all() if rid is not None}

    async def _pick_room(
        self,
        hotel_id: int,
        room_type_id: int,
        check_in: date,
        check_out: date,
    ) -> Optional[Room]:
        booked = await self._get_booked_room_ids(check_in, check_out)
        stmt = select(Room).where(
            Room.hotel_id == hotel_id,
            Room.room_type_id == room_type_id,
            Room.status == RoomStatus.available,
        )
        if booked:
            stmt = stmt.where(Room.id.notin_(booked))
        stmt = stmt.order_by(Room.room_number).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_or_create_guest(
        self,
        full_name: str,
        phone: str,
        email: Optional[str] = None,
        messenger_id: Optional[str] = None,
    ) -> Guest:
        if messenger_id:
            result = await self.db.execute(
                select(Guest).where(Guest.messenger_id == messenger_id)
            )
            guest = result.scalar_one_or_none()
            if guest:
                guest.full_name = full_name
                guest.phone = phone
                if email:
                    guest.email = email
                return guest

        result = await self.db.execute(select(Guest).where(Guest.phone == phone))
        guest = result.scalar_one_or_none()
        if guest:
            guest.full_name = full_name
            if messenger_id:
                guest.messenger_id = messenger_id
            if email:
                guest.email = email
            return guest

        guest = Guest(
            full_name=full_name,
            phone=phone,
            email=email,
            messenger_id=messenger_id,
        )
        self.db.add(guest)
        await self.db.flush()
        return guest

    @staticmethod
    def _generate_booking_code() -> str:
        suffix = "".join(random.choices(string.digits, k=6))
        return f"HTL{suffix}"

    @staticmethod
    def _to_booking_response(booking: Booking) -> BookingResponse:
        from app.schemas.booking import GuestBrief

        return BookingResponse(
            id=booking.id,
            booking_code=booking.booking_code,
            hotel_id=booking.hotel_id,
            room_id=booking.room_id,
            check_in_date=booking.check_in_date,
            check_out_date=booking.check_out_date,
            num_nights=booking.num_nights,
            num_adults=booking.num_adults,
            num_children=booking.num_children,
            status=booking.status.value,
            payment_status=booking.payment_status.value,
            total_amount=booking.total_amount,
            special_requests=booking.special_requests,
            source=booking.source,
            guest=GuestBrief.model_validate(booking.guest),
            created_at=booking.created_at,
        )
