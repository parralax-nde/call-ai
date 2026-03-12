from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db

from .schemas import (
    NotificationLogResponse,
    PreferenceResponse,
    PreferenceUpdate,
    SendEmailRequest,
    SystemAlertRequest,
    TemplateCreate,
    TemplateResponse,
    TemplateUpdate,
)
from .service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/email", response_model=NotificationLogResponse)
def send_email(
    data: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> NotificationLogResponse:
    return NotificationService.send_email(db, data)  # type: ignore[return-value]


@router.post("/email/template", response_model=NotificationLogResponse)
def send_templated_email(
    data: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> NotificationLogResponse:
    return NotificationService.send_templated_email(
        db,
        template_name=data.template_name or "",
        to=data.to,
        template_data=data.template_data or {},
        user_id=data.user_id,
    )  # type: ignore[return-value]


@router.post("/templates", response_model=TemplateResponse, status_code=201)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TemplateResponse:
    return NotificationService.create_template(db, data)  # type: ignore[return-value]


@router.get("/templates", response_model=list[TemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[TemplateResponse]:
    return NotificationService.list_templates(db)  # type: ignore[return-value]


@router.get("/templates/{template_id}", response_model=TemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TemplateResponse:
    return NotificationService.get_template(db, template_id)  # type: ignore[return-value]


@router.put("/templates/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TemplateResponse:
    return NotificationService.update_template(db, template_id, data)  # type: ignore[return-value]


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    NotificationService.delete_template(db, template_id)


@router.get("/logs", response_model=list[NotificationLogResponse])
def get_notification_logs(
    user_id: int | None = None,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[NotificationLogResponse]:
    return NotificationService.get_notification_logs(db, user_id, skip, limit)  # type: ignore[return-value]


@router.post("/alerts", response_model=list[NotificationLogResponse])
def send_system_alert(
    data: SystemAlertRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[NotificationLogResponse]:
    return NotificationService.send_system_alert(
        db, data.message, data.severity, data.admin_emails
    )  # type: ignore[return-value]


@router.get("/preferences", response_model=PreferenceResponse)
def get_preferences(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PreferenceResponse:
    user_id = int(current_user["sub"])
    return NotificationService.get_preferences(db, user_id)  # type: ignore[return-value]


@router.put("/preferences", response_model=PreferenceResponse)
def update_preferences(
    data: PreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PreferenceResponse:
    user_id = int(current_user["sub"])
    return NotificationService.update_preferences(db, user_id, data)  # type: ignore[return-value]
