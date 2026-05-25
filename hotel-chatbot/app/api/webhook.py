"""Facebook Messenger webhook — xác minh & nhận tin nhắn."""
import json
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from app.database import AsyncSessionLocal
from app.schemas.messenger import MessengerIncomingEvent
from app.services.claude_service import ClaudeService, ClaudeServiceError
from app.services.messenger_service import MessengerService, MessengerServiceError

logger = logging.getLogger(__name__)

router = APIRouter()
messenger = MessengerService()

FALLBACK_REPLY = (
    "Xin lỗi, hệ thống đang gặp sự cố. "
    "Anh/chị vui lòng thử lại sau hoặc gọi trực tiếp khách sạn ạ."
)
HUMAN_HANDOFF_NOTE = (
    "\n\n📞 Nhân viên sẽ liên hệ với anh/chị trong thời gian sớm nhất."
)


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    challenge = messenger.verify_webhook(hub_mode, hub_verify_token, hub_challenge)
    if challenge is not None:
        return PlainTextResponse(content=challenge)
    raise HTTPException(status_code=403, detail="Verify token không hợp lệ")


@router.post("")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not messenger.verify_signature(body, signature):
        raise HTTPException(status_code=403, detail="Chữ ký webhook không hợp lệ")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON không hợp lệ")

    events = messenger.parse_events(payload)
    for event in events:
        if event.user_message:
            background_tasks.add_task(handle_incoming_message, event)

    return {"status": "ok"}


async def handle_incoming_message(event: MessengerIncomingEvent) -> None:
    """Xử lý tin nhắn nền — trả 200 cho Facebook ngay, rồi gọi Claude."""
    sender_id = event.sender_id
    text = event.user_message
    if not text:
        return

    try:
        await messenger.send_typing_on(sender_id)
    except MessengerServiceError:
        logger.warning("Không gửi được typing indicator tới %s", sender_id)

    try:
        async with AsyncSessionLocal() as db:
            claude = ClaudeService(db)
            response = await claude.process_message(
                channel_user_id=sender_id,
                message=text,
                channel="messenger",
                external_id=event.message_id,
            )
            if response.duplicate:
                logger.info("Bỏ qua tin trùng mid=%s", event.message_id)
                return

            reply = response.reply
            if response.transferred_to_human:
                reply += HUMAN_HANDOFF_NOTE
            await db.commit()

        if reply:
            await messenger.send_text(sender_id, reply)

    except ClaudeServiceError as e:
        logger.error("Claude lỗi cho PSID %s: %s", sender_id, e.message)
        await _safe_send(sender_id, f"Xin lỗi, {e.message}")
    except MessengerServiceError as e:
        logger.error("Messenger lỗi cho PSID %s: %s", sender_id, e.message)
    except Exception:
        logger.exception("Lỗi xử lý tin nhắn Messenger PSID %s", sender_id)
        await _safe_send(sender_id, FALLBACK_REPLY)
    finally:
        try:
            await messenger.send_typing_off(sender_id)
        except MessengerServiceError:
            pass


async def _safe_send(recipient_id: str, text: str) -> None:
    try:
        await messenger.send_text(recipient_id, text)
    except MessengerServiceError:
        logger.exception("Không gửi được tin nhắn fallback tới %s", recipient_id)
