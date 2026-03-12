import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.exceptions import BadRequestException, ConflictException, NotFoundException

from .models import Invoice, Payment, SubscriptionPlan, UsageRecord, UserSubscription, UserWallet, WalletTransaction
from .schemas import (
    PaymentCreate,
    PesapalCallback,
    PlanCreate,
    SubscriptionUpdate,
    UsageRecordCreate,
)

PRICING = {
    "call_minutes": 0.05,
    "api_calls": 0.01,
    "message_segments": 0.02,
}


class BillingService:

    @staticmethod
    def record_usage(db: Session, data: UsageRecordCreate) -> UsageRecord:
        total_cost = data.quantity * data.unit_cost
        record = UsageRecord(
            user_id=data.user_id,
            usage_type=data.usage_type,
            quantity=data.quantity,
            unit_cost=data.unit_cost,
            total_cost=total_cost,
            reference_id=data.reference_id,
            recorded_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_usage_summary(
        db: Session, user_id: int, period_start: datetime, period_end: datetime
    ) -> dict:
        records = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.user_id == user_id,
                UsageRecord.recorded_at >= period_start,
                UsageRecord.recorded_at <= period_end,
            )
            .all()
        )

        total_call_minutes = sum(
            r.quantity for r in records if r.usage_type == "call_minutes"
        )
        total_api_calls = sum(
            r.quantity for r in records if r.usage_type == "api_calls"
        )
        total_cost = sum(r.total_cost for r in records)

        return {
            "user_id": user_id,
            "total_call_minutes": total_call_minutes,
            "total_api_calls": total_api_calls,
            "total_cost": total_cost,
            "period_start": period_start,
            "period_end": period_end,
        }

    @staticmethod
    def get_usage_records(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[UsageRecord]:
        return (
            db.query(UsageRecord)
            .filter(UsageRecord.user_id == user_id)
            .order_by(UsageRecord.recorded_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create_plan(db: Session, data: PlanCreate) -> SubscriptionPlan:
        existing = (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.name == data.name)
            .first()
        )
        if existing:
            raise ConflictException(detail=f"Plan '{data.name}' already exists")

        features_json = json.dumps(data.features) if data.features else None
        plan = SubscriptionPlan(
            name=data.name,
            description=data.description,
            price_monthly=data.price_monthly,
            price_yearly=data.price_yearly,
            call_minutes_limit=data.call_minutes_limit,
            api_calls_limit=data.api_calls_limit,
            features=features_json,
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def get_plan(db: Session, plan_id: int) -> SubscriptionPlan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise NotFoundException(detail="Subscription plan not found")
        return plan

    @staticmethod
    def list_plans(db: Session) -> list[SubscriptionPlan]:
        return (
            db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.is_active.is_(True))
            .all()
        )

    @staticmethod
    def update_plan(db: Session, plan_id: int, data: dict) -> SubscriptionPlan:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise NotFoundException(detail="Subscription plan not found")

        for key, value in data.items():
            if value is not None:
                if key == "features":
                    setattr(plan, key, json.dumps(value))
                else:
                    setattr(plan, key, value)
        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def create_subscription(
        db: Session, user_id: int, plan_id: int
    ) -> UserSubscription:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id).first()
        if not plan:
            raise NotFoundException(detail="Subscription plan not found")

        existing = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == user_id,
                UserSubscription.status == "active",
            )
            .first()
        )
        if existing:
            raise ConflictException(detail="User already has an active subscription")

        subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan_id,
            status="active",
            started_at=datetime.now(timezone.utc),
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def get_subscription(db: Session, user_id: int) -> UserSubscription:
        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .first()
        )
        if not subscription:
            raise NotFoundException(detail="Subscription not found")
        return subscription

    @staticmethod
    def update_subscription(
        db: Session, user_id: int, data: SubscriptionUpdate
    ) -> UserSubscription:
        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .first()
        )
        if not subscription:
            raise NotFoundException(detail="Subscription not found")

        if data.plan_id is not None:
            plan = (
                db.query(SubscriptionPlan)
                .filter(SubscriptionPlan.id == data.plan_id)
                .first()
            )
            if not plan:
                raise NotFoundException(detail="Subscription plan not found")
            subscription.plan_id = data.plan_id

        if data.status is not None:
            subscription.status = data.status

        subscription.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def cancel_subscription(db: Session, user_id: int) -> UserSubscription:
        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.user_id == user_id)
            .first()
        )
        if not subscription:
            raise NotFoundException(detail="Subscription not found")

        subscription.status = "cancelled"
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(subscription)
        return subscription

    @staticmethod
    def initiate_payment(db: Session, data: PaymentCreate) -> Payment:
        # MVP: create payment record; production would call Pesapal API
        payment = Payment(
            user_id=data.user_id,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            status="pending",
            transaction_id=str(uuid.uuid4()),
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def process_pesapal_callback(
        db: Session, callback: PesapalCallback
    ) -> Payment:
        payment = (
            db.query(Payment)
            .filter(Payment.transaction_id == callback.order_merchant_reference)
            .first()
        )
        if not payment:
            raise NotFoundException(detail="Payment not found")

        status_map = {
            "COMPLETED": "completed",
            "FAILED": "failed",
            "REVERSED": "refunded",
        }
        payment.status = status_map.get(callback.status.upper(), callback.status.lower())
        payment.pesapal_order_id = callback.order_tracking_id
        if payment.status == "completed":
            payment.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(payment)
        return payment

    @staticmethod
    def get_payments(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[Payment]:
        return (
            db.query(Payment)
            .filter(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def generate_invoice(
        db: Session, user_id: int, period_start: datetime, period_end: datetime
    ) -> Invoice:
        records = (
            db.query(UsageRecord)
            .filter(
                UsageRecord.user_id == user_id,
                UsageRecord.recorded_at >= period_start,
                UsageRecord.recorded_at <= period_end,
            )
            .all()
        )

        items: list[dict] = []
        total_amount = 0.0
        for record in records:
            items.append(
                {
                    "usage_type": record.usage_type,
                    "quantity": record.quantity,
                    "unit_cost": record.unit_cost,
                    "total_cost": record.total_cost,
                    "recorded_at": record.recorded_at.isoformat(),
                }
            )
            total_amount += record.total_cost

        invoice_number = f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        invoice = Invoice(
            user_id=user_id,
            invoice_number=invoice_number,
            amount=total_amount,
            status="issued",
            period_start=period_start,
            period_end=period_end,
            items=json.dumps(items),
            issued_at=datetime.now(timezone.utc),
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice

    @staticmethod
    def get_invoices(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[Invoice]:
        return (
            db.query(Invoice)
            .filter(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_invoice(db: Session, invoice_id: int) -> Invoice:
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise NotFoundException(detail="Invoice not found")
        return invoice

    # ============ Wallet Management ============

    @staticmethod
    def get_or_create_wallet(db: Session, user_id: int) -> UserWallet:
        wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
        if not wallet:
            wallet = UserWallet(user_id=user_id, balance=0.0)
            db.add(wallet)
            db.commit()
            db.refresh(wallet)
        return wallet

    @staticmethod
    def get_wallet_balance(db: Session, user_id: int) -> float:
        wallet = BillingService.get_or_create_wallet(db, user_id)
        return wallet.balance

    @staticmethod
    def add_wallet_credit(
        db: Session, user_id: int, amount: float, description: str, reference_id: str | None = None
    ) -> WalletTransaction:
        """Add credit to user's wallet"""
        wallet = BillingService.get_or_create_wallet(db, user_id)
        wallet.balance += amount
        wallet.total_recharged += amount

        transaction = WalletTransaction(
            user_id=user_id,
            transaction_type="credit",
            amount=amount,
            description=description,
            reference_id=reference_id,
            balance_after=wallet.balance,
        )
        db.add(transaction)
        db.commit()
        db.refresh(wallet)
        db.refresh(transaction)
        return transaction

    @staticmethod
    def deduct_wallet_credit(
        db: Session, user_id: int, amount: float, description: str, reference_id: str | None = None
    ) -> WalletTransaction:
        """Deduct credit from user's wallet"""
        wallet = BillingService.get_or_create_wallet(db, user_id)
        if wallet.balance < amount:
            raise BadRequestException(
                detail=f"Insufficient wallet balance. Required: ${amount}, Available: ${wallet.balance}"
            )
        
        wallet.balance -= amount
        wallet.total_spent += amount

        transaction = WalletTransaction(
            user_id=user_id,
            transaction_type="debit",
            amount=amount,
            description=description,
            reference_id=reference_id,
            balance_after=wallet.balance,
        )
        db.add(transaction)
        db.commit()
        db.refresh(wallet)
        db.refresh(transaction)
        return transaction

    @staticmethod
    def get_wallet_transactions(
        db: Session, user_id: int, skip: int = 0, limit: int = 50
    ) -> list[WalletTransaction]:
        return (
            db.query(WalletTransaction)
            .filter(WalletTransaction.user_id == user_id)
            .order_by(WalletTransaction.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def calculate_cost(usage_type: str, quantity: float) -> float:
        rate = PRICING.get(usage_type)
        if rate is None:
            raise BadRequestException(
                detail=f"Unknown usage type: {usage_type}. "
                f"Valid types: {', '.join(PRICING.keys())}"
            )
        return quantity * rate
