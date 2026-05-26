"""Pytest fixtures — SQLite in-memory, mock Claude."""
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CLAUDE_MOCK_MODE", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-admin-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-testing-minimum-32-chars")
os.environ.setdefault("FB_APP_SECRET", "")

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings

get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session():
    from app.database import AsyncSessionLocal, Base, engine
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession):
    from app.models import Hotel, Room, RoomType, RoomStatus

    hotel = Hotel(
        name="Test Hotel",
        address="1 Test St",
        phone="0900000000",
        email="test@hotel.com",
        description="Test",
    )
    db_session.add(hotel)
    await db_session.flush()

    rt = RoomType(
        hotel_id=hotel.id,
        name="Standard",
        description="Test room",
        price_per_night=Decimal("500000"),
        max_adults=2,
        max_children=1,
        amenities='["WiFi", "TV"]',
    )
    db_session.add(rt)
    await db_session.flush()

    for num in ("101", "102"):
        db_session.add(
            Room(
                hotel_id=hotel.id,
                room_type_id=rt.id,
                room_number=num,
                floor=1,
                status=RoomStatus.available,
            )
        )
    await db_session.flush()
    return {"hotel": hotel, "room_type": rt}


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    from app.database import get_db
    from app.main import app

    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers():
    """Return headers with valid admin key for X-Admin-Key authentication."""
    return {"X-Admin-Key": "test-admin-key"}


@pytest.fixture
def admin_jwt_headers():
    """Return headers with valid JWT token for Bearer authentication."""
    from app.core.security import JWTAuth
    
    token = JWTAuth.create_token(subject="test_admin", expires_delta=3600)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers_old():
    """Legacy header format - kept for backward compatibility tests."""
    return {"X-Admin-Key": "test-admin-key"}
