from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.booking import (
    AvailabilityQuery,
    AvailabilityResponse,
    BookingCreate,
    BookingResponse,
)
from app.services.booking_service import BookingService, BookingServiceError

router = APIRouter()


def _booking_error(exc: BookingServiceError) -> HTTPException:
    status = 404 if exc.code == "not_found" else 400
    return HTTPException(status_code=status, detail={"message": exc.message, "code": exc.code})


@router.get("/availability", response_model=AvailabilityResponse)
async def check_availability(
    check_in: str,
    check_out: str,
    adults: int = Query(default=1, ge=1),
    children: int = Query(default=0, ge=0),
    room_type_id: int | None = None,
    hotel_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    from datetime import date

    try:
        query = AvailabilityQuery(
            check_in=date.fromisoformat(check_in),
            check_out=date.fromisoformat(check_out),
            adults=adults,
            children=children,
            room_type_id=room_type_id,
            hotel_id=hotel_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    service = BookingService(db)
    try:
        return await service.check_availability(query)
    except BookingServiceError as e:
        raise _booking_error(e)


@router.post("", response_model=BookingResponse, status_code=201)
async def create_booking(
    data: BookingCreate,
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    try:
        return await service.create_booking(data)
    except BookingServiceError as e:
        raise _booking_error(e)


@router.get("", response_model=list[BookingResponse])
async def list_bookings_by_phone(
    phone: str = Query(..., min_length=8),
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    return await service.get_bookings_by_phone(phone)


@router.get("/{booking_code}", response_model=BookingResponse)
async def get_booking(
    booking_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    booking = await service.get_booking_by_code(booking_code)
    if not booking:
        raise HTTPException(status_code=404, detail="Không tìm thấy booking")
    return booking


@router.post("/{booking_code}/confirm", response_model=BookingResponse)
async def confirm_booking(
    booking_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    try:
        return await service.confirm_booking(booking_code)
    except BookingServiceError as e:
        raise _booking_error(e)


@router.post("/{booking_code}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_code: str,
    db: AsyncSession = Depends(get_db),
):
    service = BookingService(db)
    try:
        return await service.cancel_booking(booking_code)
    except BookingServiceError as e:
        raise _booking_error(e)
