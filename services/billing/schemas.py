import json
from datetime import datetime

from pydantic import BaseModel, model_validator


class UsageRecordCreate(BaseModel):
    user_id: int
    usage_type: str
    quantity: float
    unit_cost: float = 0.0
    reference_id: str | None = None


class UsageRecordResponse(BaseModel):
    id: int
    user_id: int
    usage_type: str
    quantity: float
    unit_cost: float
    total_cost: float
    reference_id: str | None
    recorded_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageSummary(BaseModel):
    user_id: int
    total_call_minutes: float
    total_api_calls: float
    total_cost: float
    period_start: datetime
    period_end: datetime


class PlanCreate(BaseModel):
    name: str
    description: str | None = None
    price_monthly: float
    price_yearly: float | None = None
    call_minutes_limit: int = 0
    api_calls_limit: int = 0
    features: list[str] | None = None


class PlanResponse(BaseModel):
    id: int
    name: str
    description: str | None
    price_monthly: float
    price_yearly: float | None
    call_minutes_limit: int
    api_calls_limit: int
    features: list[str] | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_features(cls, data: object) -> object:
        """Parse features from JSON string when loading from ORM."""
        if hasattr(data, "features") and isinstance(data.features, str):
            try:
                object.__setattr__(data, "features", json.loads(data.features))
            except (json.JSONDecodeError, TypeError):
                pass
        return data


class SubscriptionCreate(BaseModel):
    user_id: int
    plan_id: int


class SubscriptionResponse(BaseModel):
    id: int
    user_id: int
    plan_id: int
    status: str
    started_at: datetime
    expires_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubscriptionUpdate(BaseModel):
    plan_id: int | None = None
    status: str | None = None


class PaymentCreate(BaseModel):
    user_id: int
    amount: float
    currency: str = "KES"
    description: str | None = None


class PaymentResponse(BaseModel):
    id: int
    user_id: int
    amount: float
    currency: str
    payment_method: str
    transaction_id: str | None
    status: str
    pesapal_order_id: str | None
    description: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PesapalCallback(BaseModel):
    order_tracking_id: str
    order_merchant_reference: str
    status: str


class InvoiceResponse(BaseModel):
    id: int
    user_id: int
    invoice_number: str
    amount: float
    currency: str
    status: str
    period_start: datetime
    period_end: datetime
    items: list[dict] | str
    issued_at: datetime | None
    paid_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def parse_items(cls, data: object) -> object:
        """Parse items from JSON string when loading from ORM."""
        if hasattr(data, "items") and isinstance(data.items, str):
            try:
                object.__setattr__(data, "items", json.loads(data.items))
            except (json.JSONDecodeError, TypeError):
                pass
        return data


class CostEstimate(BaseModel):
    usage_type: str
    quantity: float
    estimated_cost: float


# ===== Wallet Schemas =====

class WalletBalanceResponse(BaseModel):
    balance: float
    currency: str
    total_recharged: float
    total_spent: float

    model_config = {"from_attributes": True}


class WalletCreditRequest(BaseModel):
    amount: float
    description: str = "Wallet top-up"


class WalletTransactionResponse(BaseModel):
    id: int
    user_id: int
    transaction_type: str
    amount: float
    description: str
    reference_id: str | None
    balance_after: float
    created_at: datetime

    model_config = {"from_attributes": True}
