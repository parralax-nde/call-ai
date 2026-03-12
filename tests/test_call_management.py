"""Comprehensive tests for the Call Management Service."""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.call_management.models import CallEvent, CallLog
from services.call_management.router import router as calls_router
from services.call_management.schemas import (
    CallEventCreate,
    CallLogCreate,
    CallLogUpdate,
    CallSearchParams,
)
from services.call_management.service import CallManagementService
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

    app.include_router(calls_router)

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
def call_log_payload() -> dict:
    return {
        "call_id": "call-abc-123",
        "user_id": 1,
        "to_number": "+15551234567",
        "from_number": "+15559876543",
        "status": "initiated",
        "ai_prompt_id": 1,
        "prompt_version": 1,
    }


# ===================================================================
# 1. Call Log Management
# ===================================================================
class TestCallLogManagement:
    def test_create_call_log(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        resp = client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["call_id"] == "call-abc-123"
        assert data["status"] == "initiated"
        assert data["to_number"] == "+15551234567"
        assert "id" in data

    def test_get_call_log(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        create_resp = client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        log_id = create_resp.json()["id"]
        resp = client.get(f"/calls/logs/{log_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == log_id
        assert resp.json()["call_id"] == "call-abc-123"

    def test_search_call_logs(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        payload2 = {**call_log_payload, "call_id": "call-def-456", "status": "completed"}
        client.post("/calls/logs", json=payload2, headers=auth_headers)

        resp = client.get("/calls/logs", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_search_call_logs_with_status_filter(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        payload2 = {**call_log_payload, "call_id": "call-def-456", "status": "completed"}
        client.post("/calls/logs", json=payload2, headers=auth_headers)

        resp = client.get("/calls/logs?status=completed", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["status"] == "completed"

    def test_update_call_log(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        call_id_str = call_log_payload["call_id"]
        resp = client.put(
            f"/calls/logs/{call_id_str}",
            json={"status": "completed", "duration_seconds": 120},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["duration_seconds"] == 120

    def test_get_call_log_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/calls/logs/9999", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 2. Call Events
# ===================================================================
class TestCallEvents:
    def test_add_call_event(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        create_resp = client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        log_id = create_resp.json()["id"]
        event_payload = {
            "call_log_id": log_id,
            "event_type": "ringing",
            "event_data": {"ring_count": 3},
        }
        resp = client.post("/calls/events", json=event_payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_type"] == "ringing"
        assert data["event_data"] == {"ring_count": 3}

    def test_get_events_for_call(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        create_resp = client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        log_id = create_resp.json()["id"]
        client.post(
            "/calls/events",
            json={"call_log_id": log_id, "event_type": "ringing", "event_data": {}},
            headers=auth_headers,
        )
        client.post(
            "/calls/events",
            json={"call_log_id": log_id, "event_type": "answered", "event_data": {}},
            headers=auth_headers,
        )
        resp = client.get(f"/calls/events/{log_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ===================================================================
# 3. Dashboard
# ===================================================================
class TestDashboard:
    def test_get_dashboard_stats(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        payload2 = {**call_log_payload, "call_id": "call-comp-1", "status": "completed"}
        client.post("/calls/logs", json=payload2, headers=auth_headers)
        payload3 = {**call_log_payload, "call_id": "call-fail-1", "status": "failed"}
        client.post("/calls/logs", json=payload3, headers=auth_headers)

        resp = client.get("/calls/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 3
        assert data["completed_calls"] == 1
        assert data["failed_calls"] == 1
        assert data["active_calls"] == 1  # "initiated" is active

    def test_dashboard_empty(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/calls/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_calls"] == 0
        assert data["avg_duration_seconds"] is None


# ===================================================================
# 4. Recordings
# ===================================================================
class TestRecordings:
    def test_get_recording_url(
        self, client: TestClient, auth_headers: dict, call_log_payload: dict
    ) -> None:
        client.post("/calls/logs", json=call_log_payload, headers=auth_headers)
        call_id_str = call_log_payload["call_id"]
        client.put(
            f"/calls/logs/{call_id_str}",
            json={"recording_url": "https://recordings.example.com/rec1.wav"},
            headers=auth_headers,
        )
        # Get the log id
        resp = client.get("/calls/logs", headers=auth_headers)
        log_id = resp.json()[0]["id"]

        resp = client.get(f"/calls/recordings/{log_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["recording_url"] == "https://recordings.example.com/rec1.wav"

    def test_get_recording_url_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/calls/recordings/9999", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 5. Service Layer Tests
# ===================================================================
class TestCallManagementServiceLayer:
    def test_create_call_log(self, db: Session) -> None:
        data = CallLogCreate(
            call_id="svc-call-1",
            user_id=1,
            to_number="+15551234567",
            from_number="+15559876543",
        )
        log = CallManagementService.create_call_log(db, data)
        assert log.id is not None
        assert log.call_id == "svc-call-1"
        assert log.status == "initiated"

    def test_get_call_log_not_found(self, db: Session) -> None:
        with pytest.raises(NotFoundException):
            CallManagementService.get_call_log(db, 9999)

    def test_update_call_log(self, db: Session) -> None:
        data = CallLogCreate(
            call_id="svc-call-2",
            user_id=1,
            to_number="+15551234567",
            from_number="+15559876543",
        )
        log = CallManagementService.create_call_log(db, data)
        update = CallLogUpdate(status="completed", duration_seconds=60)
        updated = CallManagementService.update_call_log(db, "svc-call-2", update)
        assert updated.status == "completed"
        assert updated.duration_seconds == 60

    def test_search_call_logs(self, db: Session) -> None:
        for i in range(3):
            data = CallLogCreate(
                call_id=f"search-{i}",
                user_id=1,
                to_number="+15551234567",
                from_number="+15559876543",
                status="completed" if i < 2 else "failed",
            )
            CallManagementService.create_call_log(db, data)

        params = CallSearchParams(user_id=1, status="completed")
        logs, total = CallManagementService.search_call_logs(db, params)
        assert total == 2
        assert len(logs) == 2

    def test_add_and_get_call_events(self, db: Session) -> None:
        log_data = CallLogCreate(
            call_id="evt-call-1",
            user_id=1,
            to_number="+15551234567",
            from_number="+15559876543",
        )
        log = CallManagementService.create_call_log(db, log_data)
        event_data = CallEventCreate(
            call_log_id=log.id,
            event_type="ringing",
            event_data={"detail": "test"},
        )
        event = CallManagementService.add_call_event(db, event_data)
        assert event.id is not None
        assert event.event_type == "ringing"

        events = CallManagementService.get_call_events(db, log.id)
        assert len(events) == 1

    def test_get_dashboard_stats(self, db: Session) -> None:
        for i, status in enumerate(["initiated", "completed", "failed"]):
            data = CallLogCreate(
                call_id=f"dash-{i}",
                user_id=1,
                to_number="+15551234567",
                from_number="+15559876543",
                status=status,
            )
            CallManagementService.create_call_log(db, data)

        stats = CallManagementService.get_dashboard_stats(db, user_id=1)
        assert stats["total_calls"] == 3
        assert stats["active_calls"] == 1
        assert stats["completed_calls"] == 1
        assert stats["failed_calls"] == 1

    def test_get_recording_url(self, db: Session) -> None:
        data = CallLogCreate(
            call_id="rec-call-1",
            user_id=1,
            to_number="+15551234567",
            from_number="+15559876543",
        )
        log = CallManagementService.create_call_log(db, data)
        update = CallLogUpdate(recording_url="https://example.com/rec.wav")
        CallManagementService.update_call_log(db, "rec-call-1", update)
        url = CallManagementService.get_recording_url(db, log.id, user_id=1)
        assert url == "https://example.com/rec.wav"

    def test_get_recording_url_not_found(self, db: Session) -> None:
        with pytest.raises(NotFoundException):
            CallManagementService.get_recording_url(db, 9999, user_id=1)
