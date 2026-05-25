from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api import bookings, chat, conversations, dashboard, dev, webhook

app.include_router(webhook.router, prefix="/webhook", tags=["Messenger Webhook"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["Bookings"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["Conversations"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
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
