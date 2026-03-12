from datetime import datetime

from pydantic import BaseModel


class TelnyxConfigCreate(BaseModel):
    api_key: str
    voice_profile_id: str | None = None
    webhook_url: str | None = None


class TelnyxConfigUpdate(BaseModel):
    phone_number: str | None = None
    voice_profile_id: str | None = None
    webhook_url: str | None = None


class TelnyxConfigResponse(BaseModel):
    id: int
    user_id: int
    voice_profile_id: str | None
    webhook_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class InitiateCallRequest(BaseModel):
    to_number: str
    from_number: str | None = None
    ai_prompt_id: int | None = None
    voice_config: dict | None = None


class CallResponse(BaseModel):
    id: int
    user_id: int
    telnyx_call_id: str | None
    to_number: str
    from_number: str
    status: str
    ai_prompt_id: int | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    recording_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TelnyxWebhookEvent(BaseModel):
    event_type: str
    call_control_id: str | None = None
    call_session_id: str | None = None
    payload: dict = {}


class CallStatusUpdate(BaseModel):
    status: str
    telnyx_call_id: str | None = None
    duration_seconds: int | None = None
    recording_url: str | None = None


# ===== Marketplace Schemas =====

class AvailableNumberResponse(BaseModel):
    id: int
    phone_number: str
    country_code: str
    area_code: str
    region: str | None
    monthly_price_usd: float
    setup_price_usd: float
    features: str | None
    is_available: bool

    model_config = {"from_attributes": True}


class PurchaseNumberRequest(BaseModel):
    phone_number: str
    monthly_price_usd: float = 1.0
    setup_price_usd: float = 0.0


class UserPhoneNumberResponse(BaseModel):
    id: int
    user_id: int
    phone_number: str
    country_code: str
    area_code: str | None
    monthly_price_usd: float
    features: str | None
    status: str
    purchased_at: datetime
    cancelled_at: datetime | None

    model_config = {"from_attributes": True}
