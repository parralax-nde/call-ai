from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db
from shared.exceptions import NotFoundException

from .schemas import (
    ExecuteTriggerRequest,
    ScheduleCallCreate,
    ScheduleCallUpdate,
    ScheduledCallResponse,
    TriggerCreate,
    TriggerResponse,
    TriggerUpdate,
)
from .service import SchedulerService

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])


# --- Scheduled Call Endpoints ---


@router.post("/calls", response_model=ScheduledCallResponse, status_code=201)
def schedule_call(
    data: ScheduleCallCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ScheduledCallResponse:
    call = SchedulerService.schedule_call(db, int(current_user["sub"]), data)
    return ScheduledCallResponse.model_validate(call)


@router.get("/calls", response_model=list[ScheduledCallResponse])
def list_scheduled_calls(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ScheduledCallResponse]:
    calls = SchedulerService.list_scheduled_calls(
        db, int(current_user["sub"]), skip, limit
    )
    return [ScheduledCallResponse.model_validate(c) for c in calls]


@router.get("/calls/due", response_model=list[ScheduledCallResponse])
def get_due_calls(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ScheduledCallResponse]:
    calls = SchedulerService.get_due_calls(db)
    return [ScheduledCallResponse.model_validate(c) for c in calls]


@router.get("/calls/{call_id}", response_model=ScheduledCallResponse)
def get_scheduled_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ScheduledCallResponse:
    call = SchedulerService.get_scheduled_call(db, call_id)
    return ScheduledCallResponse.model_validate(call)


@router.put("/calls/{call_id}", response_model=ScheduledCallResponse)
def update_scheduled_call(
    call_id: int,
    data: ScheduleCallUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ScheduledCallResponse:
    call = SchedulerService.update_scheduled_call(
        db, call_id, int(current_user["sub"]), data
    )
    return ScheduledCallResponse.model_validate(call)


@router.delete("/calls/{call_id}", response_model=ScheduledCallResponse)
def cancel_scheduled_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ScheduledCallResponse:
    call = SchedulerService.cancel_scheduled_call(
        db, call_id, int(current_user["sub"])
    )
    return ScheduledCallResponse.model_validate(call)


@router.post(
    "/calls/{call_id}/execute", response_model=ScheduledCallResponse
)
def execute_scheduled_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> ScheduledCallResponse:
    call = SchedulerService.execute_scheduled_call(db, call_id)
    return ScheduledCallResponse.model_validate(call)


# --- Trigger Endpoints ---


@router.post("/triggers", response_model=TriggerResponse, status_code=201)
def create_trigger(
    data: TriggerCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TriggerResponse:
    trigger = SchedulerService.create_trigger(
        db, int(current_user["sub"]), data
    )
    return TriggerResponse.model_validate(trigger)


@router.get("/triggers", response_model=list[TriggerResponse])
def list_triggers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[TriggerResponse]:
    triggers = SchedulerService.list_triggers(db, int(current_user["sub"]))
    return [TriggerResponse.model_validate(t) for t in triggers]


@router.get("/triggers/{trigger_id}", response_model=TriggerResponse)
def get_trigger(
    trigger_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TriggerResponse:
    trigger = SchedulerService.get_trigger(db, trigger_id)
    return TriggerResponse.model_validate(trigger)


@router.put("/triggers/{trigger_id}", response_model=TriggerResponse)
def update_trigger(
    trigger_id: int,
    data: TriggerUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TriggerResponse:
    trigger = SchedulerService.update_trigger(
        db, trigger_id, int(current_user["sub"]), data
    )
    return TriggerResponse.model_validate(trigger)


@router.delete("/triggers/{trigger_id}", status_code=204)
def delete_trigger(
    trigger_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    SchedulerService.delete_trigger(
        db, trigger_id, int(current_user["sub"])
    )


@router.post(
    "/triggers/{trigger_id}/fire", response_model=ScheduledCallResponse
)
def fire_trigger(
    trigger_id: int,
    data: ExecuteTriggerRequest,
    db: Session = Depends(get_db),
) -> ScheduledCallResponse:
    call = SchedulerService.fire_trigger(db, trigger_id, data.event_data)
    if not call:
        raise NotFoundException(detail="Trigger not found or inactive")
    return ScheduledCallResponse.model_validate(call)
