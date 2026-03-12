from datetime import datetime

from pydantic import BaseModel


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    template_name: str | None = None
    template_data: dict | None = None
    user_id: int | None = None


class TemplateCreate(BaseModel):
    name: str
    subject_template: str
    body_template: str


class TemplateUpdate(BaseModel):
    subject_template: str | None = None
    body_template: str | None = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    subject_template: str
    body_template: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    id: int
    user_id: int | None
    notification_type: str
    recipient: str
    subject: str
    status: str
    provider: str
    error_message: str | None
    sent_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PreferenceUpdate(BaseModel):
    email_call_completion: bool | None = None
    email_payment_reminder: bool | None = None
    email_account_alert: bool | None = None
    email_marketing: bool | None = None


class PreferenceResponse(BaseModel):
    id: int
    user_id: int
    email_call_completion: bool
    email_payment_reminder: bool
    email_account_alert: bool
    email_marketing: bool
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class SystemAlertRequest(BaseModel):
    message: str
    severity: str = "info"
    admin_emails: list[str] = []
