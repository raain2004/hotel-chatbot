"""Gọi Claude AI và thực thi actions từ phản hồi."""
import json
from datetime import date
from typing import Any, Optional

from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.actions import extract_actions, strip_actions
from app.core.prompts import build_system_prompt
from app.models import MessageRole
from app.schemas.booking import AvailabilityQuery, BookingCreate
from app.schemas.chat import ChatResponse
from app.services.booking_service import BookingService, BookingServiceError
from app.services.conversation_service import ConversationService
from app.services.notification_service import NotificationService

MAX_ACTION_ROUNDS = 3


class ClaudeServiceError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ClaudeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.booking = BookingService(db)
        self.conversation_svc = ConversationService(db)
        self.notifications = NotificationService(db)
        self._client: Optional[AsyncAnthropic] = None

    @property
    def client(self) -> AsyncAnthropic:
        if not settings.anthropic_api_key:
            raise ClaudeServiceError("ANTHROPIC_API_KEY chưa được cấu hình")
        if self._client is None:
            self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def process_message(
        self,
        channel_user_id: str,
        message: str,
        channel: str = "web",
        external_id: Optional[str] = None,
    ) -> ChatResponse:
        if external_id and await self.conversation_svc.is_message_processed(external_id):
            conversation = await self.conversation_svc.get_or_create(
                channel_user_id, channel
            )
            return ChatResponse(
                reply="",
                conversation_id=conversation.id,
                duplicate=True,
            )

        conversation = await self.conversation_svc.get_or_create(
            channel_user_id, channel
        )
        await self.conversation_svc.add_message(
            conversation.id,
            MessageRole.user,
            message,
            external_id=external_id,
        )

        if settings.claude_mock_mode:
            reply = (
                f"Xin chào! Em là trợ lý ảo khách sạn (chế độ test). "
                f"Anh/chị vừa nhắn: «{message[:100]}»"
            )
            await self.conversation_svc.add_message(
                conversation.id, MessageRole.assistant, reply
            )
            return ChatResponse(reply=reply, conversation_id=conversation.id)

        hotel = await self.booking.get_hotel_dict()
        room_types = await self.booking.get_room_types_dict()
        if not hotel:
            return ChatResponse(
                reply=(
                    "Xin lỗi, hệ thống chưa có dữ liệu khách sạn. "
                    "Vui lòng liên hệ quản trị viên."
                ),
                conversation_id=conversation.id,
            )

        system_prompt = build_system_prompt(hotel, room_types)
        ctx_summary = await self.conversation_svc.get_context_summary(conversation.id)
        if ctx_summary:
            system_prompt += f"\n\n## Context phiên hiện tại\n{ctx_summary}"

        history = await self.conversation_svc.get_claude_messages(conversation)
        transferred = False
        total_tokens = 0

        for _ in range(MAX_ACTION_ROUNDS):
            response = await self.client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.claude_max_tokens,
                system=system_prompt,
                messages=history,
            )
            total_tokens += response.usage.input_tokens + response.usage.output_tokens
            raw_text = response.content[0].text

            actions = extract_actions(raw_text)
            if not actions:
                reply = strip_actions(raw_text)
                await self.conversation_svc.add_message(
                    conversation.id,
                    MessageRole.assistant,
                    reply,
                    tokens_used=total_tokens,
                )
                return ChatResponse(
                    reply=reply,
                    conversation_id=conversation.id,
                    transferred_to_human=transferred,
                )

            action_results = []
            for action in actions:
                result, transfer = await self._execute_action(
                    action, channel_user_id, conversation.id
                )
                if transfer:
                    transferred = True
                    await self.conversation_svc.mark_waiting_human(conversation.id)
                    await self.notifications.notify_human_handoff(
                        channel_user_id, conversation.id
                    )
                action_results.append(result)

            history.append({"role": "assistant", "content": raw_text})
            history.append(
                {
                    "role": "user",
                    "content": (
                        "[Kết quả hệ thống - không hiển thị cho khách]\n"
                        + "\n".join(action_results)
                        + "\n\nHãy trả lời khách bằng tiếng Việt dựa trên kết quả trên. "
                        "Không lặp lại thẻ <action> trừ khi cần thao tác mới."
                    ),
                }
            )

        reply = "Xin lỗi, em cần thêm thời gian xử lý. Anh/chị vui lòng thử lại sau ạ."
        await self.conversation_svc.add_message(
            conversation.id, MessageRole.assistant, reply
        )
        return ChatResponse(
            reply=reply,
            conversation_id=conversation.id,
            transferred_to_human=transferred,
        )

    async def _execute_action(
        self,
        action: dict[str, Any],
        channel_user_id: str,
        conversation_id: int,
    ) -> tuple[str, bool]:
        action_type = action.get("type", "")
        transfer = False

        try:
            if action_type == "check_availability":
                await self.conversation_svc.update_context(
                    conversation_id,
                    {
                        "intent": "booking",
                        "step": "checking_availability",
                        "temp_data": {
                            "check_in": action.get("check_in"),
                            "check_out": action.get("check_out"),
                        },
                    },
                )
                result = await self.booking.check_availability(
                    AvailabilityQuery(
                        check_in=date.fromisoformat(action["check_in"]),
                        check_out=date.fromisoformat(action["check_out"]),
                        adults=int(action.get("adults", 1)),
                        children=int(action.get("children", 0)),
                        room_type_id=action.get("room_type_id"),
                    )
                )
                payload = {
                    "success": True,
                    "available": result.available,
                    "num_nights": result.num_nights,
                    "room_types": [
                        {
                            "room_type_id": rt.room_type_id,
                            "name": rt.name,
                            "price_per_night": float(rt.price_per_night),
                            "available_rooms": rt.available_rooms,
                        }
                        for rt in result.room_types
                    ],
                }

            elif action_type == "create_booking":
                result = await self.booking.create_booking(
                    BookingCreate(
                        guest_name=action["guest_name"],
                        phone=action["phone"],
                        check_in=date.fromisoformat(action["check_in"]),
                        check_out=date.fromisoformat(action["check_out"]),
                        adults=int(action.get("adults", 1)),
                        children=int(action.get("children", 0)),
                        room_type_id=int(action["room_type_id"]),
                        special_requests=action.get("special_requests"),
                        messenger_id=channel_user_id,
                    )
                )
                await self.conversation_svc.set_pending_booking(
                    conversation_id, result.id, result.guest.id
                )
                await self.conversation_svc.update_context(
                    conversation_id,
                    {"intent": "booking", "step": "completed", "temp_data": {}},
                )
                payload = {"success": True, "booking": result.model_dump(mode="json")}

            elif action_type == "get_booking":
                booking_code = action.get("booking_code")
                phone = action.get("phone")
                if booking_code:
                    booking = await self.booking.get_booking_by_code(booking_code)
                    payload = (
                        {"success": True, "booking": booking.model_dump(mode="json")}
                        if booking
                        else {"success": False, "error": "Không tìm thấy booking"}
                    )
                elif phone:
                    bookings = await self.booking.get_bookings_by_phone(phone)
                    payload = {
                        "success": bool(bookings),
                        "bookings": [b.model_dump(mode="json") for b in bookings],
                    }
                else:
                    payload = {"success": False, "error": "Thiếu booking_code hoặc phone"}

            elif action_type == "cancel_booking":
                result = await self.booking.cancel_booking(action["booking_code"])
                payload = {"success": True, "booking": result.model_dump(mode="json")}

            elif action_type == "transfer_human":
                transfer = True
                payload = {"success": True, "transferred": True}

            else:
                payload = {"success": False, "error": f"Action không hỗ trợ: {action_type}"}

        except BookingServiceError as e:
            payload = {"success": False, "error": e.message, "code": e.code}
        except (KeyError, ValueError, TypeError) as e:
            payload = {"success": False, "error": f"Dữ liệu action không hợp lệ: {e}"}

        return f"Action `{action_type}`: {json.dumps(payload, ensure_ascii=False)}", transfer
