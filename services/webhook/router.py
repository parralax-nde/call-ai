from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db

from .schemas import (
    SUPPORTED_EVENT_TYPES,
    DeliveryLogResponse,
    EventDispatchRequest,
    WebhookCreate,
    WebhookResponse,
    WebhookUpdate,
)
from .service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/", response_model=WebhookResponse)
def register_webhook(
    data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> WebhookResponse:
    user_id = int(current_user["sub"])
    webhook = WebhookService.register_webhook(db, user_id, data)
    return webhook  # type: ignore[return-value]


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[WebhookResponse]:
    user_id = int(current_user["sub"])
    return WebhookService.list_webhooks(db, user_id)  # type: ignore[return-value]


@router.get("/event-types")
def list_event_types() -> dict[str, list[str]]:
    return {"event_types": SUPPORTED_EVENT_TYPES}


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> WebhookResponse:
    user_id = int(current_user["sub"])
    return WebhookService.get_webhook(db, webhook_id, user_id)  # type: ignore[return-value]


@router.put("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    data: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> WebhookResponse:
    user_id = int(current_user["sub"])
    return WebhookService.update_webhook(db, webhook_id, user_id, data)  # type: ignore[return-value]


@router.delete("/{webhook_id}", status_code=204)
def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    user_id = int(current_user["sub"])
    WebhookService.delete_webhook(db, webhook_id, user_id)


@router.post("/dispatch", response_model=list[DeliveryLogResponse])
def dispatch_event(
    data: EventDispatchRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[DeliveryLogResponse]:
    return WebhookService.dispatch_event(db, data.event_type, data.payload)  # type: ignore[return-value]


@router.get("/{webhook_id}/deliveries", response_model=list[DeliveryLogResponse])
def get_delivery_logs(
    webhook_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[DeliveryLogResponse]:
    user_id = int(current_user["sub"])
    return WebhookService.get_delivery_logs(db, webhook_id, user_id, skip, limit)  # type: ignore[return-value]
