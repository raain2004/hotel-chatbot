"""Endpoints phát triển — seed dữ liệu mẫu."""
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import Hotel, Room, RoomType, RoomStatus

router = APIRouter()


@router.post("/seed")
async def seed_sample_data(db: AsyncSession = Depends(get_db)):
    if settings.app_env != "development":
        raise HTTPException(status_code=403, detail="Chỉ dùng trong môi trường development")

    existing = await db.execute(select(Hotel).limit(1))
    if existing.scalar_one_or_none():
        return {"message": "Dữ liệu mẫu đã tồn tại, bỏ qua seed"}

    hotel = Hotel(
        name="Grand Saigon Hotel",
        address="123 Nguyễn Huệ, Quận 1, TP.HCM",
        phone="028 3822 1234",
        email="info@grandsaigon.vn",
        description="Khách sạn 4 sao trung tâm Quận 1",
        check_in_time="14:00",
        check_out_time="12:00",
    )
    db.add(hotel)
    await db.flush()

    room_types_data = [
        ("Standard", "Phòng tiêu chuẩn, view thành phố", Decimal("800000"), 2, 1),
        ("Superior", "Phòng rộng hơn, ban công nhỏ", Decimal("1200000"), 2, 1),
        ("Deluxe", "Phòng cao cấp, view sông", Decimal("1800000"), 3, 2),
    ]
    room_types = []
    for name, desc, price, adults, children in room_types_data:
        rt = RoomType(
            hotel_id=hotel.id,
            name=name,
            description=desc,
            price_per_night=price,
            max_adults=adults,
            max_children=children,
            amenities='["WiFi", "TV", "Điều hòa", "Minibar"]',
        )
        db.add(rt)
        room_types.append(rt)

    await db.flush()

    room_number = 101
    for rt in room_types:
        for _ in range(3):
            db.add(
                Room(
                    hotel_id=hotel.id,
                    room_type_id=rt.id,
                    room_number=str(room_number),
                    floor=room_number // 100,
                    status=RoomStatus.available,
                )
            )
            room_number += 1

    await db.flush()

    return {
        "message": "Đã seed dữ liệu mẫu",
        "hotel_id": hotel.id,
        "room_types": len(room_types),
        "rooms": room_number - 101,
    }
