"""Comprehensive tests for the Scheduler Service."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.scheduler.models import CallTrigger, ScheduledCall
from services.scheduler.router import router as scheduler_router
from services.scheduler.schemas import ScheduleCallCreate, TriggerCreate, TriggerUpdate
from services.scheduler.service import SchedulerService
from shared.auth import create_access_token
from shared.database import Base, get_db
from shared.exceptions import AppException, NotFoundException

# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite://"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _build_test_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(AppException)
    async def _handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    app.include_router(scheduler_router)

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app = _build_test_app()
    with TestClient(app) as tc:
        yield tc


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = create_access_token(data={"sub": "1", "email": "test@example.com"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def future_dt() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=1)


@pytest.fixture
def schedule_payload(future_dt: datetime) -> dict:
    return {
        "to_number": "+15551234567",
        "from_number": "+15559876543",
        "ai_prompt_id": 1,
        "scheduled_at": future_dt.isoformat(),
    }


# ===================================================================
# 1. Schedule Management
# ===================================================================
class TestScheduleManagement:
    def test_schedule_one_time_call(
        self, client: TestClient, auth_headers: dict, schedule_payload: dict
    ) -> None:
        resp = client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["to_number"] == "+15551234567"
        assert data["status"] == "pending"
        assert data["user_id"] == 1
        assert "id" in data

    def test_list_scheduled_calls(
        self, client: TestClient, auth_headers: dict, schedule_payload: dict
    ) -> None:
        client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        resp = client.get("/scheduler/calls", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_scheduled_call(
        self, client: TestClient, auth_headers: dict, schedule_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        call_id = create_resp.json()["id"]
        resp = client.get(f"/scheduler/calls/{call_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == call_id

    def test_update_scheduled_call(
        self, client: TestClient, auth_headers: dict, schedule_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        call_id = create_resp.json()["id"]
        new_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        resp = client.put(
            f"/scheduler/calls/{call_id}",
            json={"scheduled_at": new_time, "status": "pending"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"

    def test_cancel_scheduled_call(
        self, client: TestClient, auth_headers: dict, schedule_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        call_id = create_resp.json()["id"]
        resp = client.delete(f"/scheduler/calls/{call_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_schedule_recurring_call(
        self, client: TestClient, auth_headers: dict, future_dt: datetime
    ) -> None:
        payload = {
            "to_number": "+15551234567",
            "scheduled_at": future_dt.isoformat(),
            "recurrence_pattern": "daily",
            "recurrence_end_date": (future_dt + timedelta(days=30)).isoformat(),
        }
        resp = client.post("/scheduler/calls", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["recurrence_pattern"] == "daily"
        assert data["recurrence_end_date"] is not None

    def test_get_scheduled_call_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/scheduler/calls/9999", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 2. Call Execution
# ===================================================================
class TestCallExecution:
    def test_execute_scheduled_call(
        self, client: TestClient, auth_headers: dict, schedule_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/calls", json=schedule_payload, headers=auth_headers)
        call_id = create_resp.json()["id"]
        resp = client.post(f"/scheduler/calls/{call_id}/execute", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "executed"
        assert data["execution_count"] == 1
        assert data["last_executed_at"] is not None

    def test_get_due_calls(
        self, client: TestClient, auth_headers: dict, db: Session
    ) -> None:
        # Insert a call with scheduled_at in the past so it's "due"
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        call = ScheduledCall(
            user_id=1,
            to_number="+15551234567",
            scheduled_at=past,
            status="pending",
        )
        db.add(call)
        db.commit()

        resp = client.get("/scheduler/calls/due", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1


# ===================================================================
# 3. Trigger Management
# ===================================================================
class TestTriggerManagement:
    @pytest.fixture
    def trigger_payload(self) -> dict:
        return {
            "name": "Test Trigger",
            "trigger_type": "webhook",
            "trigger_config": {"url": "https://example.com/hook"},
            "to_number": "+15551234567",
            "ai_prompt_id": 1,
        }

    def test_create_trigger(
        self, client: TestClient, auth_headers: dict, trigger_payload: dict
    ) -> None:
        resp = client.post("/scheduler/triggers", json=trigger_payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Trigger"
        assert data["trigger_type"] == "webhook"
        assert data["is_active"] is True

    def test_list_triggers(
        self, client: TestClient, auth_headers: dict, trigger_payload: dict
    ) -> None:
        client.post("/scheduler/triggers", json=trigger_payload, headers=auth_headers)
        resp = client.get("/scheduler/triggers", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_trigger(
        self, client: TestClient, auth_headers: dict, trigger_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/triggers", json=trigger_payload, headers=auth_headers)
        trigger_id = create_resp.json()["id"]
        resp = client.get(f"/scheduler/triggers/{trigger_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == trigger_id

    def test_update_trigger(
        self, client: TestClient, auth_headers: dict, trigger_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/triggers", json=trigger_payload, headers=auth_headers)
        trigger_id = create_resp.json()["id"]
        resp = client.put(
            f"/scheduler/triggers/{trigger_id}",
            json={"name": "Updated Trigger", "is_active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated Trigger"
        assert data["is_active"] is False

    def test_delete_trigger(
        self, client: TestClient, auth_headers: dict, trigger_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/triggers", json=trigger_payload, headers=auth_headers)
        trigger_id = create_resp.json()["id"]
        resp = client.delete(f"/scheduler/triggers/{trigger_id}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/scheduler/triggers/{trigger_id}", headers=auth_headers)
        assert resp.status_code == 404

    def test_fire_trigger(
        self, client: TestClient, auth_headers: dict, trigger_payload: dict
    ) -> None:
        create_resp = client.post("/scheduler/triggers", json=trigger_payload, headers=auth_headers)
        trigger_id = create_resp.json()["id"]
        resp = client.post(
            f"/scheduler/triggers/{trigger_id}/fire",
            json={"trigger_id": trigger_id, "event_data": {"key": "value"}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        assert data["to_number"] == "+15551234567"

    def test_get_trigger_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/scheduler/triggers/9999", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 4. Service Layer Tests
# ===================================================================
class TestSchedulerServiceLayer:
    def test_schedule_call(self, db: Session) -> None:
        data = ScheduleCallCreate(
            to_number="+15551234567",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        call = SchedulerService.schedule_call(db, user_id=1, data=data)
        assert call.id is not None
        assert call.to_number == "+15551234567"
        assert call.status == "pending"

    def test_get_scheduled_call_not_found(self, db: Session) -> None:
        with pytest.raises(NotFoundException):
            SchedulerService.get_scheduled_call(db, 9999)

    def test_cancel_scheduled_call(self, db: Session) -> None:
        data = ScheduleCallCreate(
            to_number="+15551234567",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        call = SchedulerService.schedule_call(db, user_id=1, data=data)
        cancelled = SchedulerService.cancel_scheduled_call(db, call.id, user_id=1)
        assert cancelled.status == "cancelled"

    def test_execute_scheduled_call(self, db: Session) -> None:
        data = ScheduleCallCreate(
            to_number="+15551234567",
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
        )
        call = SchedulerService.schedule_call(db, user_id=1, data=data)
        executed = SchedulerService.execute_scheduled_call(db, call.id)
        assert executed.status == "executed"
        assert executed.execution_count == 1

    def test_create_and_delete_trigger(self, db: Session) -> None:
        data = TriggerCreate(
            name="svc trigger",
            trigger_type="webhook",
            trigger_config={"url": "https://example.com"},
            to_number="+15551234567",
        )
        trigger = SchedulerService.create_trigger(db, user_id=1, data=data)
        assert trigger.id is not None
        SchedulerService.delete_trigger(db, trigger.id, user_id=1)
        with pytest.raises(NotFoundException):
            SchedulerService.get_trigger(db, trigger.id)

    def test_fire_trigger_inactive_returns_none(self, db: Session) -> None:
        data = TriggerCreate(
            name="inactive",
            trigger_type="webhook",
            trigger_config={"url": "https://example.com"},
            to_number="+15551234567",
        )
        trigger = SchedulerService.create_trigger(db, user_id=1, data=data)
        update = TriggerUpdate(is_active=False)
        SchedulerService.update_trigger(db, trigger.id, user_id=1, data=update)
        result = SchedulerService.fire_trigger(db, trigger.id, {})
        assert result is None

    def test_fire_trigger_creates_call(self, db: Session) -> None:
        data = TriggerCreate(
            name="active",
            trigger_type="webhook",
            trigger_config={"url": "https://example.com"},
            to_number="+15559999999",
        )
        trigger = SchedulerService.create_trigger(db, user_id=1, data=data)
        call = SchedulerService.fire_trigger(db, trigger.id, {"event": "test"})
        assert call is not None
        assert call.status == "queued"
        assert call.to_number == "+15559999999"
