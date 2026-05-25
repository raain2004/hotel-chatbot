"""Dependencies FastAPI — xác thực admin."""
from fastapi import Header, HTTPException

from app.config import settings


async def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")):
    if not settings.admin_api_key:
        if settings.app_env in ("development", "test"):
            return
        raise HTTPException(
            status_code=503,
            detail="ADMIN_API_KEY chưa được cấu hình",
        )
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Admin key không hợp lệ")
