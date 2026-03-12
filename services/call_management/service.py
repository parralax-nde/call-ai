import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from shared.exceptions import NotFoundException

from .models import CallEvent, CallLog
from .schemas import (
    CallEventCreate,
    CallLogCreate,
    CallLogUpdate,
    CallSearchParams,
)


class CallManagementService:
    @staticmethod
    def create_call_log(db: Session, data: CallLogCreate) -> CallLog:
        log = CallLog(
            call_id=data.call_id,
            user_id=data.user_id,
            to_number=data.to_number,
            from_number=data.from_number,
            status=data.status,
            ai_prompt_id=data.ai_prompt_id,
            prompt_version=data.prompt_version,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def update_call_log(
        db: Session, call_id_str: str, data: CallLogUpdate
    ) -> CallLog:
        log = db.query(CallLog).filter(CallLog.call_id == call_id_str).first()
        if not log:
            raise NotFoundException(detail="Call log not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(log, field, value)

        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def get_call_log(db: Session, log_id: int) -> CallLog:
        log = db.query(CallLog).filter(CallLog.id == log_id).first()
        if not log:
            raise NotFoundException(detail="Call log not found")
        return log

    @staticmethod
    def get_call_log_by_call_id(db: Session, call_id_str: str) -> CallLog:
        log = db.query(CallLog).filter(CallLog.call_id == call_id_str).first()
        if not log:
            raise NotFoundException(detail="Call log not found")
        return log

    @staticmethod
    def search_call_logs(
        db: Session, params: CallSearchParams, skip: int = 0, limit: int = 20
    ) -> tuple[list[CallLog], int]:
        query = db.query(CallLog)

        if params.user_id is not None:
            query = query.filter(CallLog.user_id == params.user_id)
        if params.status is not None:
            query = query.filter(CallLog.status == params.status)
        if params.to_number is not None:
            query = query.filter(CallLog.to_number == params.to_number)
        if params.from_number is not None:
            query = query.filter(CallLog.from_number == params.from_number)
        if params.date_from is not None:
            query = query.filter(CallLog.created_at >= params.date_from)
        if params.date_to is not None:
            query = query.filter(CallLog.created_at <= params.date_to)
        if params.ai_prompt_id is not None:
            query = query.filter(CallLog.ai_prompt_id == params.ai_prompt_id)

        total = query.count()
        logs = query.offset(skip).limit(limit).all()
        return logs, total

    @staticmethod
    def add_call_event(db: Session, data: CallEventCreate) -> CallEvent:
        event = CallEvent(
            call_log_id=data.call_log_id,
            event_type=data.event_type,
            event_data=json.dumps(data.event_data),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    @staticmethod
    def get_call_events(db: Session, call_log_id: int) -> list[CallEvent]:
        return (
            db.query(CallEvent)
            .filter(CallEvent.call_log_id == call_log_id)
            .order_by(CallEvent.occurred_at)
            .all()
        )

    @staticmethod
    def get_dashboard_stats(db: Session, user_id: int) -> dict:
        base = db.query(CallLog).filter(CallLog.user_id == user_id)

        total = base.count()
        active = base.filter(
            CallLog.status.in_(["initiated", "ringing", "answered", "in_progress"])
        ).count()
        completed = base.filter(CallLog.status == "completed").count()
        failed = base.filter(CallLog.status == "failed").count()
        avg_duration = (
            base.filter(CallLog.duration_seconds.isnot(None))
            .with_entities(func.avg(CallLog.duration_seconds))
            .scalar()
        )

        return {
            "total_calls": total,
            "active_calls": active,
            "completed_calls": completed,
            "failed_calls": failed,
            "avg_duration_seconds": (
                round(float(avg_duration), 2) if avg_duration else None
            ),
        }

    @staticmethod
    def get_recording_url(
        db: Session, call_log_id: int, user_id: int
    ) -> str | None:
        log = (
            db.query(CallLog)
            .filter(CallLog.id == call_log_id, CallLog.user_id == user_id)
            .first()
        )
        if not log:
            raise NotFoundException(detail="Call log not found")
        return log.recording_url
