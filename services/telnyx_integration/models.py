from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class TelnyxConfig(Base):
    __tablename__ = "telnyx_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    api_key_encrypted: Mapped[str] = mapped_column(String(500), nullable=False)
    voice_profile_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class UserPhoneNumber(Base):
    __tablename__ = "user_phone_numbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    telnyx_phone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_code: Mapped[str] = mapped_column(String(10), default="US")
    area_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    monthly_price_usd: Mapped[float] = mapped_column(Float, default=1.0)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of features
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, cancelled
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AvailablePhoneNumber(Base):
    __tablename__ = "available_phone_numbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    country_code: Mapped[str] = mapped_column(String(10), default="US")
    area_code: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monthly_price_usd: Mapped[float] = mapped_column(Float, default=1.0)
    setup_price_usd: Mapped[float] = mapped_column(Float, default=0.0)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class VoiceAgent(Base):
    __tablename__ = "voice_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    session_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    telnyx_agent_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="created")  # created, active, paused, deleted
    voice_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_persona_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CallRecord(Base):
    __tablename__ = "call_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    telnyx_call_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, index=True
    )
    to_number: Mapped[str] = mapped_column(String(50), nullable=False)
    from_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="initiated")
    ai_prompt_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
