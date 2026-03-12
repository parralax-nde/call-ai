from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db

from .schemas import (
    AvailableNumberResponse,
    CallResponse,
    CallStatusUpdate,
    InitiateCallRequest,
    PurchaseNumberRequest,
    TelnyxConfigCreate,
    TelnyxConfigResponse,
    TelnyxConfigUpdate,
    TelnyxWebhookEvent,
    UserPhoneNumberResponse,
)
from .service import TelnyxService

router = APIRouter(prefix="/telnyx", tags=["Telnyx Integration"])


@router.post("/config", response_model=TelnyxConfigResponse, status_code=201)
def save_config(
    data: TelnyxConfigCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TelnyxConfigResponse:
    config = TelnyxService.save_config(db, int(current_user["sub"]), data)
    return TelnyxConfigResponse.model_validate(config)


@router.get("/config", response_model=TelnyxConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TelnyxConfigResponse:
    config = TelnyxService.get_config(db, int(current_user["sub"]))
    return TelnyxConfigResponse.model_validate(config)


@router.put("/config", response_model=TelnyxConfigResponse)
def update_config(
    data: TelnyxConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> TelnyxConfigResponse:
    config = TelnyxService.update_config(db, int(current_user["sub"]), data)
    return TelnyxConfigResponse.model_validate(config)


@router.post("/calls", response_model=CallResponse, status_code=201)
def initiate_call(
    call_data: InitiateCallRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallResponse:
    call = TelnyxService.initiate_call(db, int(current_user["sub"]), call_data)
    return CallResponse.model_validate(call)


@router.get("/calls", response_model=list[CallResponse])
def list_calls(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[CallResponse]:
    calls = TelnyxService.list_calls(db, int(current_user["sub"]), skip, limit)
    return [CallResponse.model_validate(c) for c in calls]


@router.get("/calls/{call_id}", response_model=CallResponse)
def get_call(
    call_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallResponse:
    call = TelnyxService.get_call(db, call_id)
    return CallResponse.model_validate(call)


@router.post("/webhooks")
def receive_webhook(event: TelnyxWebhookEvent, db: Session = Depends(get_db)) -> dict:
    result = TelnyxService.process_webhook(db, event)
    if result:
        return {"status": "processed", "call_id": result.id}
    return {"status": "ignored"}


@router.put("/calls/{call_id}/status", response_model=CallResponse)
def update_call_status(
    call_id: int,
    status_data: CallStatusUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> CallResponse:
    call = TelnyxService.update_call_status(db, str(call_id), status_data)
    return CallResponse.model_validate(call)


# ===== Number Marketplace Endpoints =====


@router.get("/marketplace/numbers", response_model=list[AvailableNumberResponse])
async def search_available_numbers(
    country: str = Query("US"),
    area_code: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
) -> list[AvailableNumberResponse]:
    numbers = await TelnyxService.search_available_numbers(area_code, country)
    return [AvailableNumberResponse(**n) for n in numbers]


@router.post("/purchase", response_model=UserPhoneNumberResponse, status_code=201)
async def purchase_phone_number(
    data: PurchaseNumberRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserPhoneNumberResponse:
    number = await TelnyxService.purchase_phone_number(
        db, int(current_user["sub"]), data.phone_number,
    )
    return UserPhoneNumberResponse.model_validate(number)


@router.get("/user-numbers", response_model=list[UserPhoneNumberResponse])
def get_user_phone_numbers(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[UserPhoneNumberResponse]:
    numbers = TelnyxService.get_user_phone_numbers(db, int(current_user["sub"]))
    return [UserPhoneNumberResponse.model_validate(n) for n in numbers]


@router.delete("/numbers/{number_id}", response_model=UserPhoneNumberResponse)
async def cancel_phone_number(
    number_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> UserPhoneNumberResponse:
    number = await TelnyxService.cancel_phone_number(db, int(current_user["sub"]), number_id)
    return UserPhoneNumberResponse.model_validate(number)
