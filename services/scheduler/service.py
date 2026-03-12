import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.exceptions import NotFoundException

from .models import CallTrigger, ScheduledCall
from .schemas import (
    ScheduleCallCreate,
    ScheduleCallUpdate,
    TriggerCreate,
    TriggerUpdate,
)


class SchedulerService:
    # --- Scheduled Call CRUD ---

    @staticmethod
    def schedule_call(
        db: Session, user_id: int, data: ScheduleCallCreate
    ) -> ScheduledCall:
        call = ScheduledCall(
            user_id=user_id,
            to_number=data.to_number,
            from_number=data.from_number,
            ai_prompt_id=data.ai_prompt_id,
            scheduled_at=data.scheduled_at,
            recurrence_pattern=data.recurrence_pattern,
            recurrence_end_date=data.recurrence_end_date,
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def get_scheduled_call(db: Session, call_id: int) -> ScheduledCall:
        call = (
            db.query(ScheduledCall).filter(ScheduledCall.id == call_id).first()
        )
        if not call:
            raise NotFoundException(detail="Scheduled call not found")
        return call

    @staticmethod
    def list_scheduled_calls(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[ScheduledCall]:
        return (
            db.query(ScheduledCall)
            .filter(ScheduledCall.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_scheduled_call(
        db: Session, call_id: int, user_id: int, data: ScheduleCallUpdate
    ) -> ScheduledCall:
        call = (
            db.query(ScheduledCall)
            .filter(ScheduledCall.id == call_id, ScheduledCall.user_id == user_id)
            .first()
        )
        if not call:
            raise NotFoundException(detail="Scheduled call not found")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(call, field, value)

        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def cancel_scheduled_call(
        db: Session, call_id: int, user_id: int
    ) -> ScheduledCall:
        call = (
            db.query(ScheduledCall)
            .filter(ScheduledCall.id == call_id, ScheduledCall.user_id == user_id)
            .first()
        )
        if not call:
            raise NotFoundException(detail="Scheduled call not found")

        call.status = "cancelled"
        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def execute_scheduled_call(db: Session, call_id: int) -> ScheduledCall:
        call = (
            db.query(ScheduledCall).filter(ScheduledCall.id == call_id).first()
        )
        if not call:
            raise NotFoundException(detail="Scheduled call not found")

        call.status = "executed"
        call.last_executed_at = datetime.now(timezone.utc)
        call.execution_count += 1
        db.commit()
        db.refresh(call)
        return call

    @staticmethod
    def get_due_calls(db: Session) -> list[ScheduledCall]:
        now = datetime.now(timezone.utc)
        return (
            db.query(ScheduledCall)
            .filter(
                ScheduledCall.status == "pending",
                ScheduledCall.scheduled_at <= now,
            )
            .all()
        )

    # --- Trigger CRUD ---

    @staticmethod
    def create_trigger(
        db: Session, user_id: int, data: TriggerCreate
    ) -> CallTrigger:
        trigger = CallTrigger(
            user_id=user_id,
            name=data.name,
            trigger_type=data.trigger_type,
            trigger_config=json.dumps(data.trigger_config),
            to_number=data.to_number,
            ai_prompt_id=data.ai_prompt_id,
        )
        db.add(trigger)
        db.commit()
        db.refresh(trigger)
        return trigger

    @staticmethod
    def get_trigger(db: Session, trigger_id: int) -> CallTrigger:
        trigger = (
            db.query(CallTrigger).filter(CallTrigger.id == trigger_id).first()
        )
        if not trigger:
            raise NotFoundException(detail="Call trigger not found")
        return trigger

    @staticmethod
    def list_triggers(db: Session, user_id: int) -> list[CallTrigger]:
        return (
            db.query(CallTrigger)
            .filter(CallTrigger.user_id == user_id)
            .all()
        )

    @staticmethod
    def update_trigger(
        db: Session, trigger_id: int, user_id: int, data: TriggerUpdate
    ) -> CallTrigger:
        trigger = (
            db.query(CallTrigger)
            .filter(CallTrigger.id == trigger_id, CallTrigger.user_id == user_id)
            .first()
        )
        if not trigger:
            raise NotFoundException(detail="Call trigger not found")

        update_data = data.model_dump(exclude_unset=True)
        if "trigger_config" in update_data:
            update_data["trigger_config"] = json.dumps(update_data["trigger_config"])

        for field, value in update_data.items():
            setattr(trigger, field, value)

        db.commit()
        db.refresh(trigger)
        return trigger

    @staticmethod
    def delete_trigger(db: Session, trigger_id: int, user_id: int) -> None:
        trigger = (
            db.query(CallTrigger)
            .filter(CallTrigger.id == trigger_id, CallTrigger.user_id == user_id)
            .first()
        )
        if not trigger:
            raise NotFoundException(detail="Call trigger not found")
        db.delete(trigger)
        db.commit()

    @staticmethod
    def fire_trigger(
        db: Session, trigger_id: int, event_data: dict
    ) -> ScheduledCall | None:
        trigger = (
            db.query(CallTrigger).filter(CallTrigger.id == trigger_id).first()
        )
        if not trigger or not trigger.is_active:
            return None

        call = ScheduledCall(
            user_id=trigger.user_id,
            to_number=trigger.to_number,
            ai_prompt_id=trigger.ai_prompt_id,
            scheduled_at=datetime.now(timezone.utc),
            status="queued",
        )
        db.add(call)
        db.commit()
        db.refresh(call)
        return call
