from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    secret_key: str = "changeme"

    # Database
    database_url: str = "postgresql+asyncpg://hotelbot:hotelbot123@localhost:5432/hotel_chatbot"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # Claude AI
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 1024
    claude_mock_mode: bool = False

    # Admin / Dashboard
    admin_api_key: str = ""
    notify_webhook_url: str = ""

    # Facebook Messenger
    fb_page_access_token: str = ""
    fb_verify_token: str = "hotel_verify_token"
    fb_app_secret: str = ""
    fb_graph_api_version: str = "v21.0"

    # Monitoring
    sentry_dsn: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
