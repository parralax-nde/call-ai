from datetime import datetime

from pydantic import BaseModel, field_validator

SUPPORTED_EVENT_TYPES: list[str] = [
    "call_initiated",
    "call_completed",
    "call_failed",
    "call_answered",
    "recording_available",
    "payment_successful",
    "payment_failed",
    "schedule_executed",
]


class WebhookCreate(BaseModel):
    url: str
    event_types: list[str]

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, v: list[str]) -> list[str]:
        invalid = [et for et in v if et not in SUPPORTED_EVENT_TYPES]
        if invalid:
            raise ValueError(
                f"Unsupported event types: {invalid}. "
                f"Supported: {SUPPORTED_EVENT_TYPES}"
            )
        return v


class WebhookUpdate(BaseModel):
    url: str | None = None
    event_types: list[str] | None = None
    is_active: bool | None = None

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            invalid = [et for et in v if et not in SUPPORTED_EVENT_TYPES]
            if invalid:
                raise ValueError(
                    f"Unsupported event types: {invalid}. "
                    f"Supported: {SUPPORTED_EVENT_TYPES}"
                )
        return v


class WebhookResponse(BaseModel):
    id: int
    user_id: int
    url: str
    event_types: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DeliveryLogResponse(BaseModel):
    id: int
    webhook_id: int
    event_type: str
    payload: str
    response_status: int | None
    response_body: str | None
    success: bool
    attempt_number: int
    error_message: str | None
    delivered_at: datetime

    model_config = {"from_attributes": True}


class EventDispatchRequest(BaseModel):
    event_type: str
    payload: dict
