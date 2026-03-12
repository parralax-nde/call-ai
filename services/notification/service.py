from datetime import datetime, timezone

from jinja2 import Template
from sqlalchemy.orm import Session

from shared.exceptions import NotFoundException

from .models import EmailTemplate, NotificationLog, NotificationPreference
from .schemas import (
    PreferenceUpdate,
    SendEmailRequest,
    TemplateCreate,
    TemplateUpdate,
)


class NotificationService:
    @staticmethod
    def send_email(db: Session, request: SendEmailRequest) -> NotificationLog:
        log = NotificationLog(
            user_id=request.user_id,
            notification_type="email",
            recipient=request.to,
            subject=request.subject,
            body=request.body,
            status="sent",
            provider="resend",
            sent_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def send_templated_email(
        db: Session,
        template_name: str,
        to: str,
        template_data: dict,
        user_id: int | None = None,
    ) -> NotificationLog:
        template = NotificationService.get_template_by_name(db, template_name)

        subject = Template(template.subject_template).render(**template_data)
        body = Template(template.body_template).render(**template_data)

        request = SendEmailRequest(
            to=to,
            subject=subject,
            body=body,
            user_id=user_id,
        )
        return NotificationService.send_email(db, request)

    @staticmethod
    def create_template(db: Session, data: TemplateCreate) -> EmailTemplate:
        template = EmailTemplate(
            name=data.name,
            subject_template=data.subject_template,
            body_template=data.body_template,
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def get_template(db: Session, template_id: int) -> EmailTemplate:
        template = (
            db.query(EmailTemplate)
            .filter(EmailTemplate.id == template_id)
            .first()
        )
        if not template:
            raise NotFoundException(detail="Template not found")
        return template

    @staticmethod
    def get_template_by_name(db: Session, name: str) -> EmailTemplate:
        template = (
            db.query(EmailTemplate)
            .filter(EmailTemplate.name == name)
            .first()
        )
        if not template:
            raise NotFoundException(detail=f"Template '{name}' not found")
        return template

    @staticmethod
    def list_templates(db: Session) -> list[EmailTemplate]:
        return db.query(EmailTemplate).all()

    @staticmethod
    def update_template(
        db: Session, template_id: int, data: TemplateUpdate
    ) -> EmailTemplate:
        template = NotificationService.get_template(db, template_id)
        if data.subject_template is not None:
            template.subject_template = data.subject_template
        if data.body_template is not None:
            template.body_template = data.body_template
        db.commit()
        db.refresh(template)
        return template

    @staticmethod
    def delete_template(db: Session, template_id: int) -> None:
        template = NotificationService.get_template(db, template_id)
        db.delete(template)
        db.commit()

    @staticmethod
    def get_notification_logs(
        db: Session,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[NotificationLog]:
        query = db.query(NotificationLog)
        if user_id is not None:
            query = query.filter(NotificationLog.user_id == user_id)
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def send_system_alert(
        db: Session,
        message: str,
        severity: str,
        admin_emails: list[str],
    ) -> list[NotificationLog]:
        logs: list[NotificationLog] = []
        subject = f"[{severity.upper()}] System Alert"

        for email in admin_emails:
            log = NotificationLog(
                notification_type="system_alert",
                recipient=email,
                subject=subject,
                body=message,
                status="sent",
                provider="resend",
                sent_at=datetime.now(timezone.utc),
            )
            db.add(log)
            logs.append(log)

        db.commit()
        for log in logs:
            db.refresh(log)
        return logs

    @staticmethod
    def get_preferences(db: Session, user_id: int) -> NotificationPreference:
        pref = (
            db.query(NotificationPreference)
            .filter(NotificationPreference.user_id == user_id)
            .first()
        )
        if not pref:
            pref = NotificationPreference(user_id=user_id)
            db.add(pref)
            db.commit()
            db.refresh(pref)
        return pref

    @staticmethod
    def update_preferences(
        db: Session, user_id: int, data: PreferenceUpdate
    ) -> NotificationPreference:
        pref = NotificationService.get_preferences(db, user_id)
        if data.email_call_completion is not None:
            pref.email_call_completion = data.email_call_completion
        if data.email_payment_reminder is not None:
            pref.email_payment_reminder = data.email_payment_reminder
        if data.email_account_alert is not None:
            pref.email_account_alert = data.email_account_alert
        if data.email_marketing is not None:
            pref.email_marketing = data.email_marketing
        db.commit()
        db.refresh(pref)
        return pref

    @staticmethod
    def check_preference(
        db: Session, user_id: int, notification_type: str
    ) -> bool:
        pref = NotificationService.get_preferences(db, user_id)
        preference_map = {
            "email_call_completion": pref.email_call_completion,
            "email_payment_reminder": pref.email_payment_reminder,
            "email_account_alert": pref.email_account_alert,
            "email_marketing": pref.email_marketing,
        }
        return preference_map.get(notification_type, True)
