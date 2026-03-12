from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db
from shared.exceptions import ForbiddenException, UnauthorizedException

from .schemas import (
    CostEstimate,
    InvoiceResponse,
    PaymentCreate,
    PaymentResponse,
    PesapalCallback,
    PlanCreate,
    PlanResponse,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
    UsageRecordCreate,
    UsageRecordResponse,
    UsageSummary,
    WalletBalanceResponse,
    WalletCreditRequest,
    WalletTransactionResponse,
)
from .service import BillingService

router = APIRouter(prefix="/billing", tags=["Billing & Payments"])
billing_service = BillingService()


def _get_user_id(current_user: dict) -> int:
    try:
        return int(current_user["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedException(
            detail="Invalid token: missing or invalid subject"
        ) from exc


def _require_admin(current_user: dict) -> None:
    if not current_user.get("is_admin", False):
        raise ForbiddenException(detail="Admin access required")


@router.post("/usage", response_model=UsageRecordResponse, status_code=201)
def record_usage(
    data: UsageRecordCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageRecordResponse:
    _get_user_id(current_user)
    record = billing_service.record_usage(db, data)
    return UsageRecordResponse.model_validate(record)


@router.get("/usage", response_model=list[UsageRecordResponse])
def get_usage_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UsageRecordResponse]:
    user_id = _get_user_id(current_user)
    records = billing_service.get_usage_records(db, user_id, skip, limit)
    return [UsageRecordResponse.model_validate(r) for r in records]


@router.get("/usage/summary", response_model=UsageSummary)
def get_usage_summary(
    period_start: datetime = Query(...),
    period_end: datetime = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsageSummary:
    user_id = _get_user_id(current_user)
    summary = billing_service.get_usage_summary(db, user_id, period_start, period_end)
    return UsageSummary(**summary)


@router.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(
    data: PlanCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanResponse:
    _require_admin(current_user)
    plan = billing_service.create_plan(db, data)
    return PlanResponse.model_validate(plan)


@router.get("/plans", response_model=list[PlanResponse])
def list_plans(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PlanResponse]:
    _get_user_id(current_user)
    plans = billing_service.list_plans(db)
    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlanResponse:
    _get_user_id(current_user)
    plan = billing_service.get_plan(db, plan_id)
    return PlanResponse.model_validate(plan)


@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
def create_subscription(
    data: SubscriptionCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    user_id = _get_user_id(current_user)
    subscription = billing_service.create_subscription(db, user_id, data.plan_id)
    return SubscriptionResponse.model_validate(subscription)


@router.get("/subscriptions", response_model=SubscriptionResponse)
def get_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    user_id = _get_user_id(current_user)
    subscription = billing_service.get_subscription(db, user_id)
    return SubscriptionResponse.model_validate(subscription)


@router.put("/subscriptions", response_model=SubscriptionResponse)
def update_subscription(
    data: SubscriptionUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    user_id = _get_user_id(current_user)
    subscription = billing_service.update_subscription(db, user_id, data)
    return SubscriptionResponse.model_validate(subscription)


@router.delete("/subscriptions", response_model=SubscriptionResponse)
def cancel_subscription(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    user_id = _get_user_id(current_user)
    subscription = billing_service.cancel_subscription(db, user_id)
    return SubscriptionResponse.model_validate(subscription)


@router.post("/payments", response_model=PaymentResponse, status_code=201)
def initiate_payment(
    data: PaymentCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    _get_user_id(current_user)
    payment = billing_service.initiate_payment(db, data)
    return PaymentResponse.model_validate(payment)


@router.get("/payments", response_model=list[PaymentResponse])
def get_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    user_id = _get_user_id(current_user)
    payments = billing_service.get_payments(db, user_id, skip, limit)
    return [PaymentResponse.model_validate(p) for p in payments]


@router.post("/payments/pesapal/callback", response_model=PaymentResponse)
def pesapal_callback(
    data: PesapalCallback,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    payment = billing_service.process_pesapal_callback(db, data)
    return PaymentResponse.model_validate(payment)


@router.post("/invoices/generate", response_model=InvoiceResponse, status_code=201)
def generate_invoice(
    period_start: datetime = Query(...),
    period_end: datetime = Query(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    user_id = _get_user_id(current_user)
    invoice = billing_service.generate_invoice(db, user_id, period_start, period_end)
    return InvoiceResponse.model_validate(invoice)


@router.get("/invoices", response_model=list[InvoiceResponse])
def get_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InvoiceResponse]:
    user_id = _get_user_id(current_user)
    invoices = billing_service.get_invoices(db, user_id, skip, limit)
    return [InvoiceResponse.model_validate(i) for i in invoices]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    _get_user_id(current_user)
    invoice = billing_service.get_invoice(db, invoice_id)
    return InvoiceResponse.model_validate(invoice)


@router.get("/cost-estimate", response_model=CostEstimate)
def estimate_cost(
    usage_type: str = Query(...),
    quantity: float = Query(..., gt=0),
    current_user: dict = Depends(get_current_user),
) -> CostEstimate:
    _get_user_id(current_user)
    estimated_cost = billing_service.calculate_cost(usage_type, quantity)
    return CostEstimate(
        usage_type=usage_type,
        quantity=quantity,
        estimated_cost=estimated_cost,
    )


# ===== Wallet Endpoints =====


@router.get("/wallet/balance", response_model=WalletBalanceResponse)
def get_wallet_balance(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletBalanceResponse:
    user_id = _get_user_id(current_user)
    wallet = billing_service.get_or_create_wallet(db, user_id)
    return WalletBalanceResponse.model_validate(wallet)


@router.post("/wallet/credit", response_model=WalletTransactionResponse, status_code=201)
def add_wallet_credit(
    data: WalletCreditRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WalletTransactionResponse:
    user_id = _get_user_id(current_user)
    transaction = billing_service.add_wallet_credit(
        db, user_id, data.amount, data.description
    )
    return WalletTransactionResponse.model_validate(transaction)


@router.get("/wallet/transactions", response_model=list[WalletTransactionResponse])
def get_wallet_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WalletTransactionResponse]:
    user_id = _get_user_id(current_user)
    txns = billing_service.get_wallet_transactions(db, user_id, skip, limit)
    return [WalletTransactionResponse.model_validate(t) for t in txns]
