import pytest


@pytest.mark.asyncio
async def test_dashboard_stats(client, seeded_db, admin_headers):
    r = await client.get("/api/dashboard/stats", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert "total_bookings" in data
    assert "unread_notifications" in data


@pytest.mark.asyncio
async def test_dashboard_requires_admin_key(client, seeded_db):
    r = await client.get("/api/dashboard/stats")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_notifications_after_booking(client, seeded_db, admin_headers):
    rt_id = seeded_db["room_type"].id
    await client.post(
        "/api/bookings",
        json={
            "guest_name": "Notify Test",
            "phone": "0900111222",
            "check_in": "2026-10-01",
            "check_out": "2026-10-03",
            "adults": 2,
            "room_type_id": rt_id,
        },
    )
    r = await client.get("/api/dashboard/notifications", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
