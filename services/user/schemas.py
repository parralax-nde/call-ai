from datetime import datetime

from pydantic import BaseModel


class ProfileCreate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    timezone: str = "UTC"


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    timezone: str | None = None
    notification_email: bool | None = None


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: str | None
    phone_number: str | None
    timezone: str
    notification_email: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleAssign(BaseModel):
    user_id: int
    role: str


class RoleResponse(BaseModel):
    id: int | None
    user_id: int
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: int
    user_id: int
    key_prefix: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    api_key: str = ""


class AccountSettings(BaseModel):
    timezone: str | None = None
    notification_email: bool | None = None


class NumberPurchaseRequest(BaseModel):
    phone_number: str


class OwnedNumberResponse(BaseModel):
    id: int
    user_id: int
    phone_number: str
    monthly_price_usd: float
    status: str
    purchased_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceNumber(BaseModel):
    phone_number: str
    monthly_price_usd: float = 1.0


class ContactCreate(BaseModel):
    full_name: str
    phone_number: str
    email: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ContactUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    email: str | None = None
    notes: str | None = None
    tags: list[str] | None = None


class ContactResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone_number: str
    email: str | None
    notes: str | None
    tags: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
