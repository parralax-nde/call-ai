import json
from datetime import datetime

from pydantic import BaseModel, model_validator


class ServiceHealthResponse(BaseModel):
    id: int
    service_name: str
    status: str
    last_check_at: datetime | None
    response_time_ms: float | None
    error_message: str | None
    endpoint: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceHealthUpdate(BaseModel):
    status: str
    response_time_ms: float | None = None
    error_message: str | None = None


class ServiceHealthCreate(BaseModel):
    service_name: str
    endpoint: str


class SystemOverview(BaseModel):
    total_users: int
    active_calls: int
    total_calls_today: int
    system_health: str
    services: list[ServiceHealthResponse]


class AuditLogResponse(BaseModel):
    id: int
    admin_user_id: int
    action: str
    resource_type: str
    resource_id: str | None
    details: dict | str | None
    ip_address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_details(cls, data: object) -> object:
        """Parse details from JSON string when loading from ORM."""
        if hasattr(data, "details") and isinstance(data.details, str):
            try:
                object.__setattr__(data, "details", json.loads(data.details))
            except (json.JSONDecodeError, TypeError):
                pass
        return data


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None


class ServiceConfigUpdate(BaseModel):
    service_name: str
    config_key: str
    config_value: str


class GatewayStats(BaseModel):
    total_requests: int
    avg_response_time_ms: float
    error_rate: float
    requests_per_minute: float
