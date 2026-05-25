import pytest


@pytest.mark.asyncio
async def test_availability(client, seeded_db, admin_headers):
    r = await client.get(
        "/api/bookings/availability",
        params={
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "adults": 2,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["available"] is True
    assert len(data["room_types"]) >= 1


@pytest.mark.asyncio
async def test_create_and_get_booking(client, seeded_db):
    rt_id = seeded_db["room_type"].id
    create = await client.post(
        "/api/bookings",
        json={
            "guest_name": "Nguyen Van A",
            "phone": "0912345678",
            "check_in": "2026-08-01",
            "check_out": "2026-08-03",
            "adults": 2,
            "room_type_id": rt_id,
        },
    )
    assert create.status_code == 201
    code = create.json()["booking_code"]

    get = await client.get(f"/api/bookings/{code}")
    assert get.status_code == 200
    assert get.json()["guest"]["full_name"] == "Nguyen Van A"


@pytest.mark.asyncio
async def test_cancel_booking(client, seeded_db):
    rt_id = seeded_db["room_type"].id
    create = await client.post(
        "/api/bookings",
        json={
            "guest_name": "Tran B",
            "phone": "0987654321",
            "check_in": "2026-09-01",
            "check_out": "2026-09-02",
            "adults": 1,
            "room_type_id": rt_id,
        },
    )
    code = create.json()["booking_code"]
    cancel = await client.post(f"/api/bookings/{code}/cancel")
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
