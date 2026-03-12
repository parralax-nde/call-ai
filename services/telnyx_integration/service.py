import base64
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.exceptions import NotFoundException, ConflictException

from .models import CallRecord, TelnyxConfig, UserPhoneNumber, AvailablePhoneNumber, VoiceAgent
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

        from_number = call_data.from_number or settings.OUTBOUND_CALLER_NUMBER
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

    # ============ Number Marketplace ============

    @staticmethod
    def search_available_numbers(
        db: Session, area_code: str | None = None, country_code: str = "US"
    ) -> list[AvailablePhoneNumber]:
        query = db.query(AvailablePhoneNumber).filter(
            AvailablePhoneNumber.country_code == country_code,
            AvailablePhoneNumber.is_available.is_(True),
        )
        if area_code:
            query = query.filter(AvailablePhoneNumber.area_code == area_code)
        
        return query.limit(20).all()

    @staticmethod
    def purchase_phone_number(
        db: Session, user_id: int, phone_number: str, monthly_price: float, setup_price: float
    ) -> UserPhoneNumber:
        """Purchase a phone number for the user"""
        available = (
            db.query(AvailablePhoneNumber)
            .filter(AvailablePhoneNumber.phone_number == phone_number)
            .first()
        )
        if not available or not available.is_available:
            raise NotFoundException(detail="Phone number not available")

        existing = (
            db.query(UserPhoneNumber)
            .filter(UserPhoneNumber.phone_number == phone_number)
            .first()
        )
        if existing:
            raise ConflictException(detail="Phone number already owned")

        user_number = UserPhoneNumber(
            user_id=user_id,
            phone_number=phone_number,
            area_code=available.area_code,
            country_code=available.country_code,
            monthly_price_usd=monthly_price,
            features=available.features,
            status="active",
        )
        db.add(user_number)
        
        # Mark as unavailable
        available.is_available = False
        
        db.commit()
        db.refresh(user_number)
        return user_number

    @staticmethod
    def get_user_phone_numbers(
        db: Session, user_id: int
    ) -> list[UserPhoneNumber]:
        return (
            db.query(UserPhoneNumber)
            .filter(
                UserPhoneNumber.user_id == user_id,
                UserPhoneNumber.status == "active",
            )
            .all()
        )

    @staticmethod
    def cancel_phone_number(
        db: Session, user_id: int, phone_number_id: int
    ) -> UserPhoneNumber:
        """Cancel/release a phone number"""
        number = (
            db.query(UserPhoneNumber)
            .filter(
                UserPhoneNumber.id == phone_number_id,
                UserPhoneNumber.user_id == user_id,
            )
            .first()
        )
        if not number:
            raise NotFoundException(detail="Phone number not found")

        number.status = "cancelled"
        number.cancelled_at = datetime.now(timezone.utc)

        # Mark as available again
        available = (
            db.query(AvailablePhoneNumber)
            .filter(AvailablePhoneNumber.phone_number == number.phone_number)
            .first()
        )
        if available:
            available.is_available = True

        db.commit()
        db.refresh(number)
        return number

    # ============ Voice Agent Management ============

    @staticmethod
    def create_voice_agent(
        db: Session,
        user_id: int,
        session_id: int,
        telnyx_agent_id: str,
        phone_number: str | None = None,
        ai_persona_id: int | None = None,
    ) -> VoiceAgent:
        """Create a voice agent linked to a session"""
        agent = VoiceAgent(
            user_id=user_id,
            session_id=session_id,
            telnyx_agent_id=telnyx_agent_id,
            phone_number=phone_number,
            status="created",
            ai_persona_id=ai_persona_id,
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent

    @staticmethod
    def get_voice_agent(db: Session, agent_id: int) -> VoiceAgent:
        agent = db.query(VoiceAgent).filter(VoiceAgent.id == agent_id).first()
        if not agent:
            raise NotFoundException(detail="Voice agent not found")
        return agent

    @staticmethod
    def get_session_voice_agent(db: Session, session_id: int) -> VoiceAgent | None:
        return db.query(VoiceAgent).filter(VoiceAgent.session_id == session_id).first()

    @staticmethod
    def update_voice_agent_status(
        db: Session, agent_id: int, status: str
    ) -> VoiceAgent:
        agent = db.query(VoiceAgent).filter(VoiceAgent.id == agent_id).first()
        if not agent:
            raise NotFoundException(detail="Voice agent not found")

        agent.status = status
        db.commit()
        db.refresh(agent)
        return agent
