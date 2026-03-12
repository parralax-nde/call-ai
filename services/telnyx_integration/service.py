import base64
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.exceptions import NotFoundException

from .models import CallRecord, TelnyxConfig
from .schemas import (
    CallStatusUpdate,
    InitiateCallRequest,
    TelnyxConfigCreate,
    TelnyxConfigUpdate,
    TelnyxWebhookEvent,
)


class TelnyxService:
    @staticmethod
    def save_config(db: Session, user_id: int, data: TelnyxConfigCreate) -> TelnyxConfig:
        encrypted_key = base64.b64encode(data.api_key.encode()).decode()
        config = TelnyxConfig(
            user_id=user_id,
            api_key_encrypted=encrypted_key,
            phone_number=data.phone_number,
            voice_profile_id=data.voice_profile_id,
            webhook_url=data.webhook_url,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def get_config(db: Session, user_id: int) -> TelnyxConfig:
        config = db.query(TelnyxConfig).filter(TelnyxConfig.user_id == user_id).first()
        if not config:
            raise NotFoundException(detail="Telnyx configuration not found")
        return config

    @staticmethod
    def update_config(db: Session, user_id: int, data: TelnyxConfigUpdate) -> TelnyxConfig:
        config = db.query(TelnyxConfig).filter(TelnyxConfig.user_id == user_id).first()
        if not config:
            raise NotFoundException(detail="Telnyx configuration not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)

        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def initiate_call(
        db: Session, user_id: int, call_data: InitiateCallRequest
    ) -> CallRecord:
        settings = get_settings()
        config = db.query(TelnyxConfig).filter(TelnyxConfig.user_id == user_id).first()

        default_number = config.phone_number if config else settings.OUTBOUND_CALLER_NUMBER
        from_number = call_data.from_number or default_number
        if not from_number:
            raise NotFoundException(
                detail="Outbound caller number is not configured. Set OUTBOUND_CALLER_NUMBER in .env."
            )

        call_record = CallRecord(
            user_id=user_id,
            to_number=call_data.to_number,
            from_number=from_number,
            status="initiated",
            ai_prompt_id=call_data.ai_prompt_id,
        )
        db.add(call_record)
        db.commit()
        db.refresh(call_record)
        return call_record

    @staticmethod
    def update_call_status(
        db: Session, call_id_or_telnyx_id: str, status_data: CallStatusUpdate
    ) -> CallRecord:
        call_record = None
        try:
            numeric_id = int(call_id_or_telnyx_id)
            call_record = db.query(CallRecord).filter(CallRecord.id == numeric_id).first()
        except ValueError:
            pass
        if not call_record:
            call_record = (
                db.query(CallRecord)
                .filter(CallRecord.telnyx_call_id == call_id_or_telnyx_id)
                .first()
            )
        if not call_record:
            raise NotFoundException(detail="Call record not found")

        call_record.status = status_data.status
        if status_data.telnyx_call_id:
            call_record.telnyx_call_id = status_data.telnyx_call_id
        if status_data.duration_seconds is not None:
            call_record.duration_seconds = status_data.duration_seconds
        if status_data.recording_url:
            call_record.recording_url = status_data.recording_url

        if status_data.status == "answered" and not call_record.started_at:
            call_record.started_at = datetime.now(timezone.utc)
        if status_data.status in ("completed", "failed"):
            call_record.ended_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(call_record)
        return call_record

    @staticmethod
    def get_call(db: Session, call_id: int) -> CallRecord:
        call_record = db.query(CallRecord).filter(CallRecord.id == call_id).first()
        if not call_record:
            raise NotFoundException(detail="Call record not found")
        return call_record

    @staticmethod
    def list_calls(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[CallRecord]:
        return (
            db.query(CallRecord)
            .filter(CallRecord.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def process_webhook(db: Session, event: TelnyxWebhookEvent) -> CallRecord | None:
        if not event.call_control_id:
            return None

        call_record = (
            db.query(CallRecord)
            .filter(CallRecord.telnyx_call_id == event.call_control_id)
            .first()
        )
        if not call_record:
            return None

        event_status_map = {
            "call.initiated": "initiated",
            "call.ringing": "ringing",
            "call.answered": "answered",
            "call.bridged": "in_progress",
            "call.hangup": "completed",
            "call.machine.detection.ended": "in_progress",
        }

        new_status = event_status_map.get(event.event_type)
        if new_status:
            call_record.status = new_status
            if new_status == "answered" and not call_record.started_at:
                call_record.started_at = datetime.now(timezone.utc)
            if new_status == "completed":
                call_record.ended_at = datetime.now(timezone.utc)
                if call_record.started_at:
                    delta = call_record.ended_at - call_record.started_at
                    call_record.duration_seconds = int(delta.total_seconds())

        db.commit()
        db.refresh(call_record)
        return call_record
