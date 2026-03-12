import base64
import json
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from shared.config import get_settings
from shared.exceptions import BadRequestException, NotFoundException, ConflictException

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

    # ============ Number Marketplace (Telnyx API) ============

    @staticmethod
    async def search_available_numbers(
        area_code: str | None = None, country_code: str = "US"
    ) -> list[dict]:
        """Search for available phone numbers via Telnyx API"""
        settings = get_settings()
        if not settings.TELNYX_API_KEY:
            raise BadRequestException(detail="Telnyx API key not configured. Set TELNYX_API_KEY in .env")

        params: dict = {
            "filter[country_code]": country_code,
            "filter[limit]": 20,
            "filter[features]": "sms,voice",
        }
        if area_code:
            params["filter[national_destination_code]"] = area_code

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.TELNYX_API_URL}/available_phone_numbers",
                params=params,
                headers={
                    "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
                    "Accept": "application/json",
                },
            )

        if resp.status_code != 200:
            raise BadRequestException(
                detail=f"Telnyx API error: {resp.status_code} - {resp.text[:200]}"
            )

        data = resp.json().get("data", [])
        results = []
        for num in data:
            results.append({
                "phone_number": num.get("phone_number", ""),
                "country_code": num.get("country_code", country_code),
                "region_name": num.get("region_information", [{}])[0].get("region_name") if num.get("region_information") else None,
                "region_type": num.get("region_information", [{}])[0].get("region_type") if num.get("region_information") else None,
                "monthly_cost": num.get("cost_information", {}).get("monthly_cost") if num.get("cost_information") else None,
                "features": num.get("features", []),
                "vanity_format": num.get("vanity_format"),
            })
        return results

    @staticmethod
    async def purchase_phone_number(
        db: Session, user_id: int, phone_number: str
    ) -> UserPhoneNumber:
        """Purchase a phone number via Telnyx API, then save to DB"""
        settings = get_settings()
        if not settings.TELNYX_API_KEY:
            raise BadRequestException(detail="Telnyx API key not configured")

        # Check if already owned locally
        existing = (
            db.query(UserPhoneNumber)
            .filter(UserPhoneNumber.phone_number == phone_number, UserPhoneNumber.status == "active")
            .first()
        )
        if existing:
            raise ConflictException(detail="Phone number already owned")

        # Create a number order via Telnyx API
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.TELNYX_API_URL}/number_orders",
                json={
                    "phone_numbers": [{"phone_number": phone_number}],
                },
                headers={
                    "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code not in (200, 201):
            raise BadRequestException(
                detail=f"Telnyx purchase failed: {resp.text[:200]}"
            )

        order_data = resp.json().get("data", {})
        telnyx_phone_id = None
        phone_numbers_list = order_data.get("phone_numbers", [])
        if phone_numbers_list:
            telnyx_phone_id = phone_numbers_list[0].get("id")

        # Extract area code from phone number (e.g., +12125551234 -> 212)
        area_code = None
        clean = phone_number.lstrip("+")
        if clean.startswith("1") and len(clean) >= 4:
            area_code = clean[1:4]

        user_number = UserPhoneNumber(
            user_id=user_id,
            phone_number=phone_number,
            telnyx_phone_id=telnyx_phone_id,
            area_code=area_code,
            country_code="US",
            monthly_price_usd=1.0,
            features=json.dumps(["voice", "sms"]),
            status="active",
        )
        db.add(user_number)
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
    async def cancel_phone_number(
        db: Session, user_id: int, phone_number_id: int
    ) -> UserPhoneNumber:
        """Cancel/release a phone number via Telnyx API"""
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

        # Try to delete from Telnyx if we have the telnyx_phone_id
        if number.telnyx_phone_id:
            settings = get_settings()
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    await client.delete(
                        f"{settings.TELNYX_API_URL}/phone_numbers/{number.telnyx_phone_id}",
                        headers={"Authorization": f"Bearer {settings.TELNYX_API_KEY}"},
                    )
            except Exception:
                pass  # Best-effort; still mark locally as cancelled

        number.status = "cancelled"
        number.cancelled_at = datetime.now(timezone.utc)

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
