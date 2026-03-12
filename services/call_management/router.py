from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db

from .schemas import (
    CallDashboardStats,
    CallEventCreate,
    CallEventResponse,
    CallLogCreate,
    CallLogResponse,
    CallLogUpdate,
    CallSearchParams,
)
from .service import CallManagementService

router = APIRouter(prefix="/calls", tags=["Call Management"])


@router.post("/logs", response_model=CallLogResponse, status_code=201)
def create_call_log(
    data: CallLogCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallLogResponse:
    log = CallManagementService.create_call_log(db, data)
    return CallLogResponse.model_validate(log)


@router.get("/logs", response_model=list[CallLogResponse])
def search_call_logs(
    skip: int = 0,
    limit: int = 20,
    status: str | None = None,
    to_number: str | None = None,
    from_number: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    ai_prompt_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[CallLogResponse]:
    params = CallSearchParams(
        user_id=int(current_user["sub"]),
        status=status,
        to_number=to_number,
        from_number=from_number,
        date_from=date_from,
        date_to=date_to,
        ai_prompt_id=ai_prompt_id,
    )
    logs, _total = CallManagementService.search_call_logs(db, params, skip, limit)
    return [CallLogResponse.model_validate(log) for log in logs]


@router.get("/logs/{log_id}", response_model=CallLogResponse)
def get_call_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallLogResponse:
    log = CallManagementService.get_call_log(db, log_id)
    return CallLogResponse.model_validate(log)


@router.put("/logs/{call_id}", response_model=CallLogResponse)
def update_call_log(
    call_id: str,
    data: CallLogUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallLogResponse:
    log = CallManagementService.update_call_log(db, call_id, data)
    return CallLogResponse.model_validate(log)


@router.post("/events", response_model=CallEventResponse, status_code=201)
def add_call_event(
    data: CallEventCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallEventResponse:
    event = CallManagementService.add_call_event(db, data)
    return CallEventResponse.model_validate(event)


@router.get("/events/{call_log_id}", response_model=list[CallEventResponse])
def get_call_events(
    call_log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[CallEventResponse]:
    events = CallManagementService.get_call_events(db, call_log_id)
    return [CallEventResponse.model_validate(e) for e in events]


@router.get("/dashboard", response_model=CallDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallDashboardStats:
    stats = CallManagementService.get_dashboard_stats(
        db, int(current_user["sub"])
    )
    return CallDashboardStats(**stats)


@router.get("/recordings/{call_log_id}")
def get_recording_url(
    call_log_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    url = CallManagementService.get_recording_url(
        db, call_log_id, int(current_user["sub"])
    )
    return {"recording_url": url}
