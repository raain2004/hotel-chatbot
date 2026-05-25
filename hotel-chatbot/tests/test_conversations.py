import pytest


@pytest.mark.asyncio
async def test_list_conversations_after_chat(client, seeded_db, admin_headers):
    await client.post(
        "/api/chat",
        json={"user_id": "conv-user", "message": "Đặt phòng"},
    )
    r = await client.get("/api/conversations", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_conversation_detail(client, seeded_db, admin_headers):
    chat = await client.post(
        "/api/chat",
        json={"user_id": "detail-user", "message": "Hello"},
    )
    conv_id = chat.json()["conversation_id"]
    r = await client.get(f"/api/conversations/{conv_id}", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["messages"]) >= 2
