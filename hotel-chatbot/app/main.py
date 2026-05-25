from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import settings
from app.database import init_db
from app.core.security import rate_limiter


# Initialize Sentry for error monitoring
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=settings.app_env,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if settings.app_env == "development":
        await init_db()
        print("✅ Database tables created")
    yield
    # Shutdown (nếu cần cleanup)


app = FastAPI(
    title="Hotel Chatbot API",
    description="Hệ thống chatbot quản lý khách sạn tích hợp Claude AI + Facebook Messenger",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - Restrict in production
allowed_origins = ["*"]
if settings.app_env == "production":
    allowed_origins = [
        "https://yourdomain.com",
        "https://admin.yourdomain.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all requests with JWT bypass for admin."""
    client_ip = request.client.host if request.client else "unknown"
    route_path = request.url.path
    
    # Skip rate limit for health checks and webhook verify
    if route_path in ["/health", "/webhook"]:
        return await call_next(request)
    
    # Bypass rate limit for authenticated admin users
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        from app.core.security import JWTAuth
        token = auth_header.split(" ")[1]
        if JWTAuth.verify_token(token):
            return await call_next(request)
    
    # Rate limit: 100 requests per minute per IP
    if not rate_limiter.is_allowed(f"{client_ip}:{route_path}", max_requests=100, window_seconds=60):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please try again later."},
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
            }
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = rate_limiter.get_remaining(f"{client_ip}:{route_path}", max_requests=100, window_seconds=60)
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    
    return response

from app.api import auth, bookings, chat, conversations, dashboard, dev, webhook

app.include_router(webhook.router, prefix="/webhook", tags=["Messenger Webhook"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
if settings.app_env == "development":
    app.include_router(dev.router, prefix="/api/dev", tags=["Development"])


@app.get("/")
async def root():
    return {
        "message": "Hotel Chatbot API đang chạy 🏨",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}
