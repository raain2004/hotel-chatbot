import pytest


@pytest.mark.asyncio
async def test_chat_mock_mode(client, seeded_db):
    r = await client.post(
        "/api/chat",
        json={"user_id": "user-1", "message": "Xin chào"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "test" in data["reply"].lower() or "Xin chào" in data["reply"]
    assert data["conversation_id"] > 0


@pytest.mark.asyncio
async def test_chat_idempotency(client, seeded_db):
    payload = {
        "user_id": "user-dup",
        "message": "Hello",
        "channel": "web",
    }
    r1 = await client.post("/api/chat", json=payload)
    assert r1.status_code == 200
