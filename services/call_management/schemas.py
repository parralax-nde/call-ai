import json
from datetime import datetime

from pydantic import BaseModel, model_validator


class CallLogCreate(BaseModel):
    call_id: str
    user_id: int
    to_number: str
    from_number: str
    status: str = "initiated"
    ai_prompt_id: int | None = None
    prompt_version: int | None = None


class CallLogUpdate(BaseModel):
    status: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    recording_url: str | None = None
    error_message: str | None = None


class CallLogResponse(BaseModel):
    id: int
    user_id: int
    call_id: str
    to_number: str
    from_number: str
    status: str
    ai_prompt_id: int | None
    prompt_version: int | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    recording_url: str | None
    metadata_json: str | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CallEventCreate(BaseModel):
    call_log_id: int
    event_type: str
    event_data: dict = {}


class CallEventResponse(BaseModel):
    id: int
    call_log_id: int
    event_type: str
    event_data: dict
    occurred_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_event_data(cls, data: object) -> object:
        if hasattr(data, "__table__"):
            ed_val = getattr(data, "event_data", None)
            if isinstance(ed_val, str):
                try:
                    parsed = json.loads(ed_val)
                except (json.JSONDecodeError, TypeError):
                    parsed = {}
                return {
                    c.key: (
                        parsed if c.key == "event_data" else getattr(data, c.key)
                    )
                    for c in data.__table__.columns
                }
        return data


class CallSearchParams(BaseModel):
    user_id: int | None = None
    status: str | None = None
    to_number: str | None = None
    from_number: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    ai_prompt_id: int | None = None


class CallDashboardStats(BaseModel):
    total_calls: int
    active_calls: int
    completed_calls: int
    failed_calls: int
    avg_duration_seconds: float | None = None
