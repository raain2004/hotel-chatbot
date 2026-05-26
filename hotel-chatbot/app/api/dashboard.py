from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_jwt_token
from app.database import get_db
from app.schemas.dashboard import DashboardStats, NotificationOut, RecentBookingOut
from app.services.dashboard_service import DashboardService
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db), payload: dict = Depends(verify_jwt_token)):
    """Get dashboard statistics - requires JWT authentication."""
    return await DashboardService(db).get_stats()


@router.get("/bookings/recent", response_model=list[RecentBookingOut])
async def recent_bookings(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_jwt_token),
):
    """Get recent bookings - requires JWT authentication."""
    return await DashboardService(db).get_recent_bookings(limit=limit)


@router.get("/notifications", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_jwt_token),
):
    """List notifications - requires JWT authentication."""
    items = await NotificationService(db).list_notifications(unread_only, limit)
    return [
        NotificationOut(
            id=n.id,
            type=n.type.value,
            title=n.title,
            message=n.message,
            booking_id=n.booking_id,
            conversation_id=n.conversation_id,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in items
    ]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(verify_jwt_token),
):
    """Mark notification as read - requires JWT authentication."""
    n = await NotificationService(db).mark_read(notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    return NotificationOut(
        id=n.id,
        type=n.type.value,
        title=n.title,
        message=n.message,
        booking_id=n.booking_id,
        conversation_id=n.conversation_id,
        is_read=n.is_read,
        created_at=n.created_at,
    )


@router.post("/notifications/read-all")
async def mark_all_notifications_read(db: AsyncSession = Depends(get_db), payload: dict = Depends(verify_jwt_token)):
    """Mark all notifications as read - requires JWT authentication."""
    count = await NotificationService(db).mark_all_read()
    return {"marked_read": count}
