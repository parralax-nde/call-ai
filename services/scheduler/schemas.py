import json
from datetime import datetime

from pydantic import BaseModel, model_validator


class ScheduleCallCreate(BaseModel):
    to_number: str
    from_number: str | None = None
    ai_prompt_id: int | None = None
    scheduled_at: datetime
    recurrence_pattern: str | None = None
    recurrence_end_date: datetime | None = None


class ScheduleCallUpdate(BaseModel):
    scheduled_at: datetime | None = None
    recurrence_pattern: str | None = None
    recurrence_end_date: datetime | None = None
    status: str | None = None


class ScheduledCallResponse(BaseModel):
    id: int
    user_id: int
    to_number: str
    from_number: str | None
    ai_prompt_id: int | None
    scheduled_at: datetime
    status: str
    recurrence_pattern: str | None
    recurrence_end_date: datetime | None
    last_executed_at: datetime | None
    execution_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TriggerCreate(BaseModel):
    name: str
    trigger_type: str
    trigger_config: dict
    to_number: str
    ai_prompt_id: int | None = None


class TriggerUpdate(BaseModel):
    name: str | None = None
    trigger_config: dict | None = None
    to_number: str | None = None
    is_active: bool | None = None


class TriggerResponse(BaseModel):
    id: int
    user_id: int
    name: str
    trigger_type: str
    trigger_config: dict
    to_number: str
    ai_prompt_id: int | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_trigger_config(cls, data: object) -> object:
        if hasattr(data, "__table__"):
            tc_val = getattr(data, "trigger_config", None)
            if isinstance(tc_val, str):
                try:
                    parsed = json.loads(tc_val)
                except (json.JSONDecodeError, TypeError):
                    parsed = {}
                return {
                    c.key: (
                        parsed if c.key == "trigger_config" else getattr(data, c.key)
                    )
                    for c in data.__table__.columns
                }
        return data


class ExecuteTriggerRequest(BaseModel):
    trigger_id: int
    event_data: dict = {}
