from dataclasses import dataclass
from typing import Optional


@dataclass
class MessengerIncomingEvent:
    """Sự kiện messaging đã parse từ webhook payload."""

    sender_id: str
    text: Optional[str] = None
    message_id: Optional[str] = None
    postback_payload: Optional[str] = None
    postback_title: Optional[str] = None
    is_echo: bool = False

    @property
    def user_message(self) -> Optional[str]:
        if self.is_echo:
            return None
        if self.text:
            return self.text.strip()
        if self.postback_payload:
            return self.postback_title or self.postback_payload
        return None
