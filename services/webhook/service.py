import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.exceptions import NotFoundException

from .models import WebhookDeliveryLog, WebhookRegistration
from .schemas import WebhookCreate, WebhookUpdate


class WebhookService:
    @staticmethod
    def register_webhook(
        db: Session, user_id: int, data: WebhookCreate
    ) -> WebhookRegistration:
        webhook = WebhookRegistration(
            user_id=user_id,
            url=data.url,
            event_types=json.dumps(data.event_types),
            secret=secrets.token_urlsafe(32),
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)
        return webhook

    @staticmethod
    def get_webhook(
        db: Session, webhook_id: int, user_id: int
    ) -> WebhookRegistration:
        webhook = (
            db.query(WebhookRegistration)
            .filter(
                WebhookRegistration.id == webhook_id,
                WebhookRegistration.user_id == user_id,
            )
            .first()
        )
        if not webhook:
            raise NotFoundException(detail="Webhook not found")
        return webhook

    @staticmethod
    def list_webhooks(db: Session, user_id: int) -> list[WebhookRegistration]:
        return (
            db.query(WebhookRegistration)
            .filter(WebhookRegistration.user_id == user_id)
            .all()
        )

    @staticmethod
    def update_webhook(
        db: Session, webhook_id: int, user_id: int, data: WebhookUpdate
    ) -> WebhookRegistration:
        webhook = WebhookService.get_webhook(db, webhook_id, user_id)
        if data.url is not None:
            webhook.url = data.url
        if data.event_types is not None:
            webhook.event_types = json.dumps(data.event_types)
        if data.is_active is not None:
            webhook.is_active = data.is_active
        db.commit()
        db.refresh(webhook)
        return webhook

    @staticmethod
    def delete_webhook(db: Session, webhook_id: int, user_id: int) -> None:
        webhook = WebhookService.get_webhook(db, webhook_id, user_id)
        db.delete(webhook)
        db.commit()

    @staticmethod
    def get_webhooks_for_event(
        db: Session, event_type: str
    ) -> list[WebhookRegistration]:
        all_active = (
            db.query(WebhookRegistration)
            .filter(WebhookRegistration.is_active.is_(True))
            .all()
        )
        return [
            wh
            for wh in all_active
            if event_type in json.loads(wh.event_types)
        ]

    @staticmethod
    def dispatch_event(
        db: Session, event_type: str, payload: dict
    ) -> list[WebhookDeliveryLog]:
        webhooks = WebhookService.get_webhooks_for_event(db, event_type)
        logs: list[WebhookDeliveryLog] = []

        for webhook in webhooks:
            payload_str = json.dumps(payload)
            log = WebhookDeliveryLog(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload_str,
                response_status=200,
                response_body="MVP: delivery simulated",
                success=True,
                attempt_number=1,
                delivered_at=datetime.now(timezone.utc),
            )
            db.add(log)
            logs.append(log)

        db.commit()
        for log in logs:
            db.refresh(log)
        return logs

    @staticmethod
    def sign_payload(payload: str, secret: str) -> str:
        return hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def get_delivery_logs(
        db: Session,
        webhook_id: int,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[WebhookDeliveryLog]:
        # Verify ownership
        WebhookService.get_webhook(db, webhook_id, user_id)
        return (
            db.query(WebhookDeliveryLog)
            .filter(WebhookDeliveryLog.webhook_id == webhook_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
