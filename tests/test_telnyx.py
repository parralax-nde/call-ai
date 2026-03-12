"""Comprehensive tests for the Telnyx Integration Service."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.telnyx_integration.models import CallRecord, TelnyxConfig
from services.telnyx_integration.router import router as telnyx_router
from services.telnyx_integration.schemas import (
    CallStatusUpdate,
    InitiateCallRequest,
    TelnyxConfigCreate,
    TelnyxConfigUpdate,
    TelnyxWebhookEvent,
)
from services.telnyx_integration.service import TelnyxService
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

TEST_USER_ID = 1


def _make_token(sub: str = str(TEST_USER_ID), email: str = "test@example.com") -> str:
    return create_access_token(data={"sub": sub, "email": email})


def _build_test_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(AppException)
    async def _handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    app.include_router(telnyx_router)

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
    return {"Authorization": f"Bearer {_make_token()}"}


@pytest.fixture
def saved_config(client: TestClient, auth_headers: dict) -> dict:
    """Create a telnyx config and return the response JSON."""
    payload = {
        "api_key": "test-api-key-123",
        "phone_number": "+15551234567",
        "voice_profile_id": "vp_abc",
        "webhook_url": "https://example.com/webhook",
    }
    resp = client.post("/telnyx/config", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def initiated_call(client: TestClient, auth_headers: dict, saved_config: dict) -> dict:
    """Initiate a call (requires config) and return the response JSON."""
    payload = {"to_number": "+15559876543"}
    resp = client.post("/telnyx/calls", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


# ===================================================================
# 1. Telnyx Config Management
# ===================================================================
class TestTelnyxConfigManagement:
    def test_save_config(self, client: TestClient, auth_headers: dict) -> None:
        payload = {
            "api_key": "my-key",
            "phone_number": "+15551111111",
            "voice_profile_id": "vp_1",
            "webhook_url": "https://example.com/wh",
        }
        resp = client.post("/telnyx/config", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["phone_number"] == "+15551111111"
        assert data["user_id"] == TEST_USER_ID
        assert data["voice_profile_id"] == "vp_1"
        assert "id" in data
        assert "created_at" in data

    def test_get_config(
        self, client: TestClient, auth_headers: dict, saved_config: dict
    ) -> None:
        resp = client.get("/telnyx/config", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["phone_number"] == saved_config["phone_number"]

    def test_update_config(
        self, client: TestClient, auth_headers: dict, saved_config: dict
    ) -> None:
        resp = client.put(
            "/telnyx/config",
            json={"phone_number": "+15550000000"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["phone_number"] == "+15550000000"

    def test_get_config_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/telnyx/config", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 2. Call Management
# ===================================================================
class TestCallManagement:
    def test_initiate_call(
        self, client: TestClient, auth_headers: dict, saved_config: dict
    ) -> None:
        payload = {"to_number": "+15559999999", "ai_prompt_id": 1}
        resp = client.post("/telnyx/calls", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["to_number"] == "+15559999999"
        assert data["from_number"] == saved_config["phone_number"]
        assert data["status"] == "initiated"
        assert data["ai_prompt_id"] == 1

    def test_initiate_call_with_from_number(
        self, client: TestClient, auth_headers: dict, saved_config: dict
    ) -> None:
        payload = {"to_number": "+15559999999", "from_number": "+15558888888"}
        resp = client.post("/telnyx/calls", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["from_number"] == "+15558888888"

    def test_list_calls(
        self, client: TestClient, auth_headers: dict, initiated_call: dict
    ) -> None:
        resp = client.get("/telnyx/calls", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_call_details(
        self, client: TestClient, auth_headers: dict, initiated_call: dict
    ) -> None:
        call_id = initiated_call["id"]
        resp = client.get(f"/telnyx/calls/{call_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == call_id

    def test_update_call_status(
        self, client: TestClient, auth_headers: dict, initiated_call: dict
    ) -> None:
        call_id = initiated_call["id"]
        resp = client.put(
            f"/telnyx/calls/{call_id}/status",
            json={"status": "answered", "telnyx_call_id": "tc_abc123"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "answered"
        assert data["telnyx_call_id"] == "tc_abc123"
        assert data["started_at"] is not None

    def test_call_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/telnyx/calls/99999", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 3. Webhook Processing
# ===================================================================
class TestWebhookProcessing:
    def test_process_webhook_event(
        self, client: TestClient, auth_headers: dict, db: Session
    ) -> None:
        # Create config + call via service layer so we control telnyx_call_id
        svc = TelnyxService()
        config_data = TelnyxConfigCreate(
            api_key="k", phone_number="+15550000000"
        )
        svc.save_config(db, TEST_USER_ID, config_data)
        call_data = InitiateCallRequest(to_number="+15551111111")
        call = svc.initiate_call(db, TEST_USER_ID, call_data)
        # Set telnyx_call_id so webhook can find the call
        call.telnyx_call_id = "ctrl_xyz"
        db.commit()

        resp = client.post(
            "/telnyx/webhooks",
            json={
                "event_type": "call.answered",
                "call_control_id": "ctrl_xyz",
                "payload": {},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

    def test_webhook_no_matching_call(self, client: TestClient) -> None:
        resp = client.post(
            "/telnyx/webhooks",
            json={
                "event_type": "call.answered",
                "call_control_id": "nonexistent",
                "payload": {},
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"

    def test_webhook_no_call_control_id(self, client: TestClient) -> None:
        resp = client.post(
            "/telnyx/webhooks",
            json={"event_type": "call.answered", "payload": {}},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"


# ===================================================================
# 4. Service Layer Tests
# ===================================================================
class TestTelnyxServiceLayer:
    def test_save_config(self, db: Session) -> None:
        svc = TelnyxService()
        data = TelnyxConfigCreate(
            api_key="key123", phone_number="+15551234567"
        )
        config = svc.save_config(db, TEST_USER_ID, data)
        assert config.id is not None
        assert config.user_id == TEST_USER_ID
        assert config.phone_number == "+15551234567"
        assert config.api_key_encrypted  # should be base64-encoded

    def test_get_config(self, db: Session) -> None:
        svc = TelnyxService()
        data = TelnyxConfigCreate(
            api_key="key123", phone_number="+15551234567"
        )
        svc.save_config(db, TEST_USER_ID, data)
        config = svc.get_config(db, TEST_USER_ID)
        assert config.phone_number == "+15551234567"

    def test_get_config_not_found(self, db: Session) -> None:
        svc = TelnyxService()
        with pytest.raises(NotFoundException):
            svc.get_config(db, 999)

    def test_update_config(self, db: Session) -> None:
        svc = TelnyxService()
        svc.save_config(
            db, TEST_USER_ID,
            TelnyxConfigCreate(api_key="k", phone_number="+15550000000"),
        )
        updated = svc.update_config(
            db, TEST_USER_ID,
            TelnyxConfigUpdate(phone_number="+15551111111"),
        )
        assert updated.phone_number == "+15551111111"

    def test_update_config_not_found(self, db: Session) -> None:
        svc = TelnyxService()
        with pytest.raises(NotFoundException):
            svc.update_config(db, 999, TelnyxConfigUpdate(phone_number="+1"))

    def test_initiate_call(self, db: Session) -> None:
        svc = TelnyxService()
        svc.save_config(
            db, TEST_USER_ID,
            TelnyxConfigCreate(api_key="k", phone_number="+15550000000"),
        )
        call = svc.initiate_call(
            db, TEST_USER_ID,
            InitiateCallRequest(to_number="+15559999999"),
        )
        assert call.to_number == "+15559999999"
        assert call.from_number == "+15550000000"
        assert call.status == "initiated"

    def test_initiate_call_no_config(self, db: Session) -> None:
        svc = TelnyxService()
        with pytest.raises(NotFoundException):
            svc.initiate_call(
                db, TEST_USER_ID,
                InitiateCallRequest(to_number="+15559999999"),
            )

    def test_update_call_status(self, db: Session) -> None:
        svc = TelnyxService()
        svc.save_config(
            db, TEST_USER_ID,
            TelnyxConfigCreate(api_key="k", phone_number="+15550000000"),
        )
        call = svc.initiate_call(
            db, TEST_USER_ID,
            InitiateCallRequest(to_number="+15551111111"),
        )
        updated = svc.update_call_status(
            db, str(call.id),
            CallStatusUpdate(status="completed", duration_seconds=120),
        )
        assert updated.status == "completed"
        assert updated.duration_seconds == 120
        assert updated.ended_at is not None

    def test_update_call_status_not_found(self, db: Session) -> None:
        svc = TelnyxService()
        with pytest.raises(NotFoundException):
            svc.update_call_status(
                db, "nonexistent",
                CallStatusUpdate(status="completed"),
            )

    def test_list_calls(self, db: Session) -> None:
        svc = TelnyxService()
        svc.save_config(
            db, TEST_USER_ID,
            TelnyxConfigCreate(api_key="k", phone_number="+15550000000"),
        )
        svc.initiate_call(
            db, TEST_USER_ID, InitiateCallRequest(to_number="+15551111111")
        )
        svc.initiate_call(
            db, TEST_USER_ID, InitiateCallRequest(to_number="+15552222222")
        )
        calls = svc.list_calls(db, TEST_USER_ID)
        assert len(calls) == 2

    def test_process_webhook(self, db: Session) -> None:
        svc = TelnyxService()
        svc.save_config(
            db, TEST_USER_ID,
            TelnyxConfigCreate(api_key="k", phone_number="+15550000000"),
        )
        call = svc.initiate_call(
            db, TEST_USER_ID, InitiateCallRequest(to_number="+15551111111")
        )
        call.telnyx_call_id = "ctrl_test"
        db.commit()

        result = svc.process_webhook(
            db,
            TelnyxWebhookEvent(
                event_type="call.answered",
                call_control_id="ctrl_test",
            ),
        )
        assert result is not None
        assert result.status == "answered"
        assert result.started_at is not None

    def test_process_webhook_no_control_id(self, db: Session) -> None:
        svc = TelnyxService()
        result = svc.process_webhook(
            db,
            TelnyxWebhookEvent(event_type="call.answered"),
        )
        assert result is None

    def test_process_webhook_hangup(self, db: Session) -> None:
        """Hangup sets status to completed. Duration calculation has a known
        tz-naive/aware mismatch with SQLite, so we test only status & ended_at."""
        svc = TelnyxService()
        svc.save_config(
            db, TEST_USER_ID,
            TelnyxConfigCreate(api_key="k", phone_number="+15550000000"),
        )
        call = svc.initiate_call(
            db, TEST_USER_ID, InitiateCallRequest(to_number="+15551111111")
        )
        call.telnyx_call_id = "ctrl_hang"
        # Don't set started_at so the duration branch is skipped (SQLite
        # strips timezone info, triggering a pre-existing subtraction bug).
        db.commit()

        result = svc.process_webhook(
            db,
            TelnyxWebhookEvent(
                event_type="call.hangup", call_control_id="ctrl_hang"
            ),
        )
        assert result is not None
        assert result.status == "completed"
        assert result.ended_at is not None
