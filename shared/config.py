from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AI Call Automator"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "change-me-in-production"

    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 30

    TELNYX_API_KEY: str = ""
    TELNYX_API_URL: str = "https://api.telnyx.com/v2"

    RESEND_API_KEY: str = ""

    PESAPAL_CONSUMER_KEY: str = ""
    PESAPAL_CONSUMER_SECRET: str = ""

    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    WEBHOOK_SIGNING_SECRET: str = "webhook-secret"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
