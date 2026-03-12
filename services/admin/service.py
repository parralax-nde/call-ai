import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.exceptions import ConflictException, NotFoundException

from .models import AuditLog, ServiceHealth
from .schemas import ServiceHealthUpdate


class AdminService:

    @staticmethod
    def register_service(
        db: Session, service_name: str, endpoint: str
    ) -> ServiceHealth:
        existing = (
            db.query(ServiceHealth)
            .filter(ServiceHealth.service_name == service_name)
            .first()
        )
        if existing:
            raise ConflictException(
                detail=f"Service '{service_name}' is already registered"
            )

        service = ServiceHealth(
            service_name=service_name,
            endpoint=endpoint,
            status="unknown",
        )
        db.add(service)
        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def update_service_health(
        db: Session, service_name: str, data: ServiceHealthUpdate
    ) -> ServiceHealth:
        service = (
            db.query(ServiceHealth)
            .filter(ServiceHealth.service_name == service_name)
            .first()
        )
        if not service:
            raise NotFoundException(detail=f"Service '{service_name}' not found")

        service.status = data.status
        service.last_check_at = datetime.now(timezone.utc)
        service.updated_at = datetime.now(timezone.utc)

        if data.response_time_ms is not None:
            service.response_time_ms = data.response_time_ms
        if data.error_message is not None:
            service.error_message = data.error_message
        else:
            service.error_message = None

        db.commit()
        db.refresh(service)
        return service

    @staticmethod
    def get_all_services_health(db: Session) -> list[ServiceHealth]:
        return db.query(ServiceHealth).all()

    @staticmethod
    def get_service_health(db: Session, service_name: str) -> ServiceHealth:
        service = (
            db.query(ServiceHealth)
            .filter(ServiceHealth.service_name == service_name)
            .first()
        )
        if not service:
            raise NotFoundException(detail=f"Service '{service_name}' not found")
        return service

    @staticmethod
    def get_system_overview(db: Session) -> dict:
        services = db.query(ServiceHealth).all()

        unhealthy_count = sum(1 for s in services if s.status == "unhealthy")
        degraded_count = sum(1 for s in services if s.status == "degraded")

        if unhealthy_count > 0:
            system_health = "unhealthy"
        elif degraded_count > 0:
            system_health = "degraded"
        else:
            system_health = "healthy"

        return {
            "total_users": 0,
            "active_calls": 0,
            "total_calls_today": 0,
            "system_health": system_health,
            "services": services,
        }

    @staticmethod
    def log_audit_event(
        db: Session,
        admin_user_id: int,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        details: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        details_json = json.dumps(details) if details else None
        audit_log = AuditLog(
            admin_user_id=admin_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details_json,
            ip_address=ip_address,
        )
        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)
        return audit_log

    @staticmethod
    def get_audit_logs(
        db: Session, skip: int = 0, limit: int = 50
    ) -> list[AuditLog]:
        return (
            db.query(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_gateway_stats(db: Session) -> dict:
        # MVP: return mock gateway analytics
        return {
            "total_requests": 0,
            "avg_response_time_ms": 0.0,
            "error_rate": 0.0,
            "requests_per_minute": 0.0,
        }
