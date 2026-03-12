import json
from datetime import datetime

from pydantic import BaseModel, model_validator


class PromptCreate(BaseModel):
    name: str
    content: str
    persona_id: int | None = None


class PromptUpdate(BaseModel):
    name: str | None = None
    content: str | None = None
    persona_id: int | None = None
    is_active: bool | None = None


class PromptResponse(BaseModel):
    id: int
    user_id: int
    name: str
    content: str
    version: int
    is_active: bool
    persona_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonaCreate(BaseModel):
    name: str
    description: str | None = None
    tone: str = "professional"
    traits: list[str] | None = None


class PersonaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    tone: str | None = None
    traits: list[str] | None = None


class PersonaResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    tone: str
    traits: list[str] | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_traits(cls, data: object) -> object:
        if hasattr(data, "__table__"):
            traits_val = getattr(data, "traits", None)
            if isinstance(traits_val, str):
                try:
                    parsed = json.loads(traits_val)
                except (json.JSONDecodeError, TypeError):
                    parsed = None
                return {
                    c.key: (parsed if c.key == "traits" else getattr(data, c.key))
                    for c in data.__table__.columns
                }
        return data


class FlowCreate(BaseModel):
    name: str
    flow_config: dict
    prompt_template_id: int | None = None


class FlowUpdate(BaseModel):
    name: str | None = None
    flow_config: dict | None = None
    prompt_template_id: int | None = None


class FlowResponse(BaseModel):
    id: int
    user_id: int
    name: str
    flow_config: dict
    prompt_template_id: int | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_flow_config(cls, data: object) -> object:
        if hasattr(data, "__table__"):
            fc_val = getattr(data, "flow_config", None)
            if isinstance(fc_val, str):
                try:
                    parsed = json.loads(fc_val)
                except (json.JSONDecodeError, TypeError):
                    parsed = {}
                return {
                    c.key: (parsed if c.key == "flow_config" else getattr(data, c.key))
                    for c in data.__table__.columns
                }
        return data


class VersionResponse(BaseModel):
    id: int
    prompt_template_id: int
    version: int
    content: str
    created_by: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ===== Session Schemas =====

class SessionCreate(BaseModel):
    name: str
    description: str | None = None
    persona_id: int | None = None
    prompt_template_id: int | None = None
    target_phone_number: str | None = None
    from_phone_number: str | None = None
    scheduled_at: datetime | None = None
    recurrence_pattern: str | None = None
    recurrence_end_date: datetime | None = None
    status: str = "draft"


class SessionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    persona_id: int | None = None
    prompt_template_id: int | None = None
    target_phone_number: str | None = None
    from_phone_number: str | None = None
    scheduled_at: datetime | None = None
    recurrence_pattern: str | None = None
    recurrence_end_date: datetime | None = None
    status: str | None = None


class SessionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    persona_id: int | None
    prompt_template_id: int | None
    voice_agent_id: int | None
    target_phone_number: str | None
    from_phone_number: str | None
    scheduled_at: datetime | None
    recurrence_pattern: str | None
    recurrence_end_date: datetime | None
    status: str
    execution_count: int
    last_executed_at: datetime | None
    is_template: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}
