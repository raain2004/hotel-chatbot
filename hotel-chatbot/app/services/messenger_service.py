"""Gửi/nhận tin nhắn qua Facebook Messenger Platform API."""
import hashlib
import hmac
import logging
from typing import Any, Optional

import httpx

from app.config import settings
from app.schemas.messenger import MessengerIncomingEvent

logger = logging.getLogger(__name__)

MESSENGER_TEXT_LIMIT = 2000


class MessengerServiceError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class MessengerService:
    def __init__(self):
        self.page_access_token = settings.fb_page_access_token
        self.app_secret = settings.fb_app_secret
        self.verify_token = settings.fb_verify_token
        self.api_version = settings.fb_graph_api_version
        self._base_url = f"https://graph.facebook.com/{self.api_version}"

    def verify_webhook(
        self, mode: Optional[str], token: Optional[str], challenge: Optional[str]
    ) -> Optional[str]:
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        if not self.app_secret:
            if settings.app_env in ("development", "test"):
                logger.warning("FB_APP_SECRET trống — bỏ qua xác thực chữ ký")
                return True
            logger.error("FB_APP_SECRET bắt buộc trong production")
            return False

        if not signature_header.startswith("sha256="):
            return False

        expected = hmac.new(
            self.app_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        received = signature_header[7:]
        return hmac.compare_digest(expected, received)

    def parse_events(self, body: dict[str, Any]) -> list[MessengerIncomingEvent]:
        events: list[MessengerIncomingEvent] = []
        if body.get("object") != "page":
            return events

        for entry in body.get("entry", []):
            for messaging in entry.get("messaging", []):
                sender_id = messaging.get("sender", {}).get("id")
                if not sender_id:
                    continue

                if "message" in messaging:
                    msg = messaging["message"]
                    if msg.get("is_echo"):
                        continue
                    text = msg.get("text")
                    if not text and msg.get("attachments"):
                        text = "[Khách gửi file/ảnh — hiện chỉ hỗ trợ tin nhắn văn bản]"
                    events.append(
                        MessengerIncomingEvent(
                            sender_id=sender_id,
                            text=text,
                            message_id=msg.get("mid"),
                            is_echo=False,
                        )
                    )
                elif "postback" in messaging:
                    pb = messaging["postback"]
                    events.append(
                        MessengerIncomingEvent(
                            sender_id=sender_id,
                            postback_payload=pb.get("payload"),
                            postback_title=pb.get("title"),
                        )
                    )

        return events

    async def send_text(self, recipient_id: str, text: str) -> None:
        if not self.page_access_token:
            raise MessengerServiceError("FB_PAGE_ACCESS_TOKEN chưa được cấu hình")

        for chunk in self._chunk_text(text):
            await self._call_send_api(
                {
                    "recipient": {"id": recipient_id},
                    "message": {"text": chunk},
                }
            )

    async def send_typing_on(self, recipient_id: str) -> None:
        await self._send_sender_action(recipient_id, "typing_on")

    async def send_typing_off(self, recipient_id: str) -> None:
        await self._send_sender_action(recipient_id, "typing_off")

    async def _send_sender_action(self, recipient_id: str, action: str) -> None:
        if not self.page_access_token:
            return
        await self._call_send_api(
            {
                "recipient": {"id": recipient_id},
                "sender_action": action,
            }
        )

    async def _call_send_api(self, payload: dict[str, Any]) -> None:
        url = f"{self._base_url}/me/messages"
        params = {"access_token": self.page_access_token}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=params, json=payload)
            if response.status_code != 200:
                logger.error(
                    "Messenger Send API lỗi %s: %s",
                    response.status_code,
                    response.text,
                )
                raise MessengerServiceError(
                    f"Không gửi được tin nhắn: {response.status_code}"
                )

    @staticmethod
    def _chunk_text(text: str, limit: int = MESSENGER_TEXT_LIMIT) -> list[str]:
        if len(text) <= limit:
            return [text]
        chunks = []
        remaining = text
        while remaining:
            chunks.append(remaining[:limit])
            remaining = remaining[limit:]
        return chunks
