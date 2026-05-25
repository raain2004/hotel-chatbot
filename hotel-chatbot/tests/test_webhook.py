import json

import pytest

from app.config import settings
from app.schemas.messenger import MessengerIncomingEvent


@pytest.mark.asyncio
async def test_webhook_verify(client):
    r = await client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.fb_verify_token,
            "hub.challenge": "challenge123",
        },
    )
    assert r.status_code == 200
    assert r.text == "challenge123"


@pytest.mark.asyncio
async def test_webhook_receive_returns_ok(client, seeded_db):
    payload = {
        "object": "page",
        "entry": [
            {
                "messaging": [
                    {
                        "sender": {"id": "psid-123"},
                        "message": {"mid": "mid-001", "text": "Xin chào"},
                    }
                ]
            }
        ],
    }
    r = await client.post(
        "/webhook",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_handle_incoming_message_direct(seeded_db, monkeypatch):
    sent = []

    async def mock_send_text(recipient_id: str, text: str):
        sent.append((recipient_id, text))

    async def mock_typing(*_args, **_kwargs):
        pass

    from app.api.webhook import handle_incoming_message
    from app.api import webhook as wh

    monkeypatch.setattr(wh.messenger, "send_text", mock_send_text)
    monkeypatch.setattr(wh.messenger, "send_typing_on", mock_typing)
    monkeypatch.setattr(wh.messenger, "send_typing_off", mock_typing)

    event = MessengerIncomingEvent(
        sender_id="psid-456",
        text="Muốn đặt phòng",
        message_id="mid-direct",
    )
    await handle_incoming_message(event)
    assert len(sent) == 1
    assert sent[0][0] == "psid-456"
    assert len(sent[0][1]) > 0
