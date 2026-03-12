from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db
from shared.exceptions import ForbiddenException, UnauthorizedException

from .schemas import (
    AuditLogResponse,
    GatewayStats,
    ServiceHealthCreate,
    ServiceHealthResponse,
    ServiceHealthUpdate,
    SystemOverview,
)
from .service import AdminService

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])
admin_service = AdminService()


def _get_user_id(current_user: dict) -> int:
    try:
        return int(current_user["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedException(
            detail="Invalid token: missing or invalid subject"
        ) from exc


def _require_admin(current_user: dict) -> None:
    if not current_user.get("is_admin", False):
        raise ForbiddenException(detail="Admin access required")


@router.get("/health", response_model=list[ServiceHealthResponse])
def get_all_services_health(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ServiceHealthResponse]:
    _require_admin(current_user)
    services = admin_service.get_all_services_health(db)
    return [ServiceHealthResponse.model_validate(s) for s in services]


@router.get("/health/{service_name}", response_model=ServiceHealthResponse)
def get_service_health(
    service_name: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServiceHealthResponse:
    _require_admin(current_user)
    service = admin_service.get_service_health(db, service_name)
    return ServiceHealthResponse.model_validate(service)


@router.post("/health", response_model=ServiceHealthResponse, status_code=201)
def register_service(
    data: ServiceHealthCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServiceHealthResponse:
    _require_admin(current_user)
    user_id = _get_user_id(current_user)
    service = admin_service.register_service(db, data.service_name, data.endpoint)
    admin_service.log_audit_event(
        db, user_id, "register_service", "service", data.service_name
    )
    return ServiceHealthResponse.model_validate(service)


@router.put("/health/{service_name}", response_model=ServiceHealthResponse)
def update_service_health(
    service_name: str,
    data: ServiceHealthUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ServiceHealthResponse:
    _require_admin(current_user)
    service = admin_service.update_service_health(db, service_name, data)
    return ServiceHealthResponse.model_validate(service)


@router.get("/overview", response_model=SystemOverview)
def get_system_overview(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SystemOverview:
    _require_admin(current_user)
    overview = admin_service.get_system_overview(db)
    return SystemOverview(
        total_users=overview["total_users"],
        active_calls=overview["active_calls"],
        total_calls_today=overview["total_calls_today"],
        system_health=overview["system_health"],
        services=[
            ServiceHealthResponse.model_validate(s) for s in overview["services"]
        ],
    )


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    _require_admin(current_user)
    logs = admin_service.get_audit_logs(db, skip, limit)
    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/gateway-stats", response_model=GatewayStats)
def get_gateway_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GatewayStats:
    _require_admin(current_user)
    stats = admin_service.get_gateway_stats(db)
    return GatewayStats(**stats)
