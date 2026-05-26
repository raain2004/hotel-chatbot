"""Authentication API - JWT token management."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import JWTAuth, verify_jwt_token
from app.config import settings

router = APIRouter()


class TokenRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class TokenRefresh(BaseModel):
    refresh_token: str | None = None


@router.post("/token", response_model=TokenResponse)
async def login(data: TokenRequest):
    """
    Login and get JWT access token.
    
    For now, uses simple username/password check against admin_api_key.
    In production, replace with proper user database & password hashing.
    """
    # Simple auth - in production, use proper user DB + bcrypt
    if not settings.admin_api_key or data.password != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token
    token = JWTAuth.create_token(subject=data.username, expires_delta=3600)
    
    return TokenResponse(access_token=token, expires_in=3600)


@router.get("/me")
async def get_current_user(payload: dict = Depends(verify_jwt_token)):
    """Get current authenticated user info."""
    return {
        "sub": payload.get("sub"),
        "exp": payload.get("exp"),
        "iat": payload.get("iat"),
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: TokenRefresh = None):
    """
    Refresh access token.
    
    Currently returns new token without validation.
    In production, validate refresh token and implement rotation.
    """
    token = JWTAuth.create_token(subject="admin", expires_delta=3600)
    return TokenResponse(access_token=token, expires_in=3600)


@router.post("/logout")
async def logout(payload: dict = Depends(verify_jwt_token)):
    """
    Logout - invalidate token (client-side only for now).
    
    In production, add token to blacklist in Redis.
    """
    return {"message": "Logged out successfully"}
