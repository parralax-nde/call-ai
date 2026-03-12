from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class CallSession(Base):
    """Represents an AI voice call session with integrated scheduling"""
    __tablename__ = "call_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # AI Configuration
    voice: Mapped[str] = mapped_column(String(100), default="Telnyx.Polly.Joanna")
    prompt_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    voice_agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Phone & Contact Details
    target_phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    from_phone_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(20), nullable=True)  # daily, weekly, monthly
    recurrence_end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Status & Execution
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft, active, paused, completed, cancelled
    execution_count: Mapped[int] = mapped_column(Integer, default=0)
    last_executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Metadata
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    persona_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class AiPersona(Base):
    __tablename__ = "ai_personas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str] = mapped_column(String(100), default="professional")
    traits: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ConversationalFlow(Base):
    __tablename__ = "conversational_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    flow_config: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_template_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_template_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
