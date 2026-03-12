"""Comprehensive tests for the User Service."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.user.models import UserApiKey, UserProfile, UserRole
from services.user.router import router as user_router
from services.user.service import UserService
from shared.auth import create_access_token
from shared.database import Base, get_db
from shared.exceptions import (
    AppException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)

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

USER_ID = 1
ADMIN_USER_ID = 99


def _make_user_token() -> str:
    """Create a valid JWT token for a regular user (sub must be int-convertible)."""
    return create_access_token(data={"sub": str(USER_ID), "email": "test@example.com"})


def _make_admin_token() -> str:
    """Create a valid JWT token for an admin user."""
    return create_access_token(
        data={"sub": str(ADMIN_USER_ID), "email": "admin@example.com", "is_admin": True}
    )


def _user_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_user_token()}"}


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_make_admin_token()}"}


def _build_test_app() -> FastAPI:
    """Create a FastAPI app wired to the test DB."""
    app = FastAPI()

    @app.exception_handler(AppException)
    async def _handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    app.include_router(user_router)

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


# ===================================================================
# 1. Profile Management (HTTP)
# ===================================================================
class TestProfileManagement:
    def test_create_profile(self, client: TestClient) -> None:
        resp = client.post(
            "/users/profile",
            json={"full_name": "Test User", "phone_number": "+1234567890", "timezone": "US/Eastern"},
            headers=_user_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == USER_ID
        assert data["full_name"] == "Test User"
        assert data["phone_number"] == "+1234567890"
        assert data["timezone"] == "US/Eastern"
        assert data["notification_email"] is True
        assert "id" in data
        assert "created_at" in data

    def test_create_profile_defaults(self, client: TestClient) -> None:
        resp = client.post(
            "/users/profile",
            json={},
            headers=_user_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["timezone"] == "UTC"
        assert data["full_name"] is None
        assert data["phone_number"] is None

    def test_create_profile_duplicate_returns_409(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post("/users/profile", json={"full_name": "First"}, headers=headers)
        resp = client.post("/users/profile", json={"full_name": "Second"}, headers=headers)
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"].lower()

    def test_get_own_profile(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post(
            "/users/profile",
            json={"full_name": "My Profile"},
            headers=headers,
        )
        resp = client.get("/users/profile", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "My Profile"
        assert data["user_id"] == USER_ID

    def test_get_profile_returns_404_when_not_exists(self, client: TestClient) -> None:
        resp = client.get("/users/profile", headers=_user_headers())
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_update_profile(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post(
            "/users/profile",
            json={"full_name": "Original Name", "timezone": "UTC"},
            headers=headers,
        )
        resp = client.put(
            "/users/profile",
            json={"full_name": "Updated Name", "timezone": "Africa/Nairobi"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Updated Name"
        assert data["timezone"] == "Africa/Nairobi"

    def test_update_profile_partial(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post(
            "/users/profile",
            json={"full_name": "Keep This", "phone_number": "+111"},
            headers=headers,
        )
        resp = client.put(
            "/users/profile",
            json={"phone_number": "+222"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "Keep This"
        assert data["phone_number"] == "+222"

    def test_update_nonexistent_profile_returns_404(self, client: TestClient) -> None:
        resp = client.put(
            "/users/profile",
            json={"full_name": "No Profile"},
            headers=_user_headers(),
        )
        assert resp.status_code == 404

    def test_delete_profile(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post("/users/profile", json={"full_name": "Delete Me"}, headers=headers)
        resp = client.delete("/users/profile", headers=headers)
        assert resp.status_code == 204

        # Confirm it's gone
        resp = client.get("/users/profile", headers=headers)
        assert resp.status_code == 404

    def test_delete_nonexistent_profile_returns_404(self, client: TestClient) -> None:
        resp = client.delete("/users/profile", headers=_user_headers())
        assert resp.status_code == 404


# ===================================================================
# 2. Role Management (HTTP)
# ===================================================================
class TestRoleManagement:
    def test_get_default_role_for_user(self, client: TestClient) -> None:
        resp = client.get(f"/users/roles/{USER_ID}", headers=_user_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == USER_ID
        assert data["role"] == "user"

    def test_assign_role_admin_only(self, client: TestClient) -> None:
        resp = client.post(
            "/users/roles",
            json={"user_id": USER_ID, "role": "editor"},
            headers=_admin_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == USER_ID
        assert data["role"] == "editor"

    def test_assign_role_non_admin_returns_403(self, client: TestClient) -> None:
        resp = client.post(
            "/users/roles",
            json={"user_id": USER_ID, "role": "admin"},
            headers=_user_headers(),
        )
        assert resp.status_code == 403
        assert "admin" in resp.json()["detail"].lower()

    def test_assign_role_updates_existing(self, client: TestClient) -> None:
        headers = _admin_headers()
        client.post("/users/roles", json={"user_id": USER_ID, "role": "editor"}, headers=headers)
        resp = client.post("/users/roles", json={"user_id": USER_ID, "role": "admin"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["role"] == "admin"

    def test_get_user_role_after_assignment(self, client: TestClient) -> None:
        client.post(
            "/users/roles",
            json={"user_id": USER_ID, "role": "moderator"},
            headers=_admin_headers(),
        )
        resp = client.get(f"/users/roles/{USER_ID}", headers=_user_headers())
        assert resp.status_code == 200
        assert resp.json()["role"] == "moderator"


# ===================================================================
# 3. API Key Management (HTTP)
# ===================================================================
class TestApiKeyManagement:
    def test_generate_api_key(self, client: TestClient) -> None:
        resp = client.post(
            "/users/api-keys",
            json={"name": "my-key"},
            headers=_user_headers(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "my-key"
        assert data["user_id"] == USER_ID
        assert data["is_active"] is True
        assert "api_key" in data
        assert len(data["api_key"]) > 0
        assert "key_prefix" in data

    def test_list_api_keys(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post("/users/api-keys", json={"name": "key-1"}, headers=headers)
        client.post("/users/api-keys", json={"name": "key-2"}, headers=headers)

        resp = client.get("/users/api-keys", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = {k["name"] for k in data}
        assert names == {"key-1", "key-2"}

    def test_list_api_keys_empty(self, client: TestClient) -> None:
        resp = client.get("/users/api-keys", headers=_user_headers())
        assert resp.status_code == 200
        assert resp.json() == []

    def test_revoke_api_key(self, client: TestClient) -> None:
        headers = _user_headers()
        create_resp = client.post(
            "/users/api-keys", json={"name": "revoke-me"}, headers=headers
        )
        key_id = create_resp.json()["id"]

        resp = client.delete(f"/users/api-keys/{key_id}", headers=headers)
        assert resp.status_code == 204

        # Key should still appear in the list but be inactive
        keys = client.get("/users/api-keys", headers=headers).json()
        revoked = [k for k in keys if k["id"] == key_id]
        assert len(revoked) == 1
        assert revoked[0]["is_active"] is False

    def test_revoke_nonexistent_api_key_returns_404(self, client: TestClient) -> None:
        resp = client.delete("/users/api-keys/9999", headers=_user_headers())
        assert resp.status_code == 404

    def test_revoke_other_users_key_returns_404(self, client: TestClient) -> None:
        # Admin creates a key
        create_resp = client.post(
            "/users/api-keys", json={"name": "admin-key"}, headers=_admin_headers()
        )
        key_id = create_resp.json()["id"]

        # Regular user tries to revoke it
        resp = client.delete(f"/users/api-keys/{key_id}", headers=_user_headers())
        assert resp.status_code == 404


# ===================================================================
# 4. Account Settings (HTTP)
# ===================================================================
class TestAccountSettings:
    def test_update_settings(self, client: TestClient) -> None:
        headers = _user_headers()
        # Must create profile first since settings updates the profile
        client.post(
            "/users/profile",
            json={"full_name": "Settings User", "timezone": "UTC"},
            headers=headers,
        )

        resp = client.put(
            "/users/settings",
            json={"timezone": "Europe/London", "notification_email": False},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "Europe/London"
        assert data["notification_email"] is False

    def test_update_settings_partial(self, client: TestClient) -> None:
        headers = _user_headers()
        client.post(
            "/users/profile",
            json={"full_name": "Partial", "timezone": "UTC"},
            headers=headers,
        )

        resp = client.put(
            "/users/settings",
            json={"notification_email": False},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["timezone"] == "UTC"
        assert data["notification_email"] is False

    def test_update_settings_no_profile_returns_404(self, client: TestClient) -> None:
        resp = client.put(
            "/users/settings",
            json={"timezone": "Asia/Tokyo"},
            headers=_user_headers(),
        )
        assert resp.status_code == 404


# ===================================================================
# 5. Service Layer Tests
# ===================================================================
class TestUserServiceLayer:
    # --- Profile ---
    def test_create_profile(self, db: Session) -> None:
        svc = UserService()
        profile = svc.create_profile(db, USER_ID, {"full_name": "Service Test", "timezone": "UTC"})
        assert profile.user_id == USER_ID
        assert profile.full_name == "Service Test"
        assert profile.id is not None

    def test_create_profile_duplicate_raises_conflict(self, db: Session) -> None:
        svc = UserService()
        svc.create_profile(db, USER_ID, {"full_name": "First"})
        with pytest.raises(ConflictException):
            svc.create_profile(db, USER_ID, {"full_name": "Second"})

    def test_get_profile(self, db: Session) -> None:
        svc = UserService()
        svc.create_profile(db, USER_ID, {"full_name": "Getter"})
        profile = svc.get_profile(db, USER_ID)
        assert profile.full_name == "Getter"

    def test_get_profile_not_found_raises(self, db: Session) -> None:
        svc = UserService()
        with pytest.raises(NotFoundException):
            svc.get_profile(db, 9999)

    def test_update_profile(self, db: Session) -> None:
        svc = UserService()
        svc.create_profile(db, USER_ID, {"full_name": "Before", "timezone": "UTC"})
        updated = svc.update_profile(db, USER_ID, {"full_name": "After"})
        assert updated.full_name == "After"
        assert updated.timezone == "UTC"
        assert updated.updated_at is not None

    def test_update_profile_not_found_raises(self, db: Session) -> None:
        svc = UserService()
        with pytest.raises(NotFoundException):
            svc.update_profile(db, 9999, {"full_name": "Nobody"})

    def test_delete_profile(self, db: Session) -> None:
        svc = UserService()
        svc.create_profile(db, USER_ID, {"full_name": "Delete Me"})
        svc.delete_profile(db, USER_ID)
        with pytest.raises(NotFoundException):
            svc.get_profile(db, USER_ID)

    def test_delete_profile_not_found_raises(self, db: Session) -> None:
        svc = UserService()
        with pytest.raises(NotFoundException):
            svc.delete_profile(db, 9999)

    # --- Roles ---
    def test_assign_role(self, db: Session) -> None:
        svc = UserService()
        role = svc.assign_role(db, USER_ID, "editor")
        assert role.user_id == USER_ID
        assert role.role == "editor"
        assert role.id is not None

    def test_assign_role_updates_existing(self, db: Session) -> None:
        svc = UserService()
        svc.assign_role(db, USER_ID, "editor")
        role = svc.assign_role(db, USER_ID, "admin")
        assert role.role == "admin"

    def test_get_user_role_default(self, db: Session) -> None:
        svc = UserService()
        role = svc.get_user_role(db, USER_ID)
        assert role.user_id == USER_ID
        assert role.role == "user"
        assert role.id is None  # not persisted

    def test_get_user_role_assigned(self, db: Session) -> None:
        svc = UserService()
        svc.assign_role(db, USER_ID, "manager")
        role = svc.get_user_role(db, USER_ID)
        assert role.role == "manager"
        assert role.id is not None

    # --- API Keys ---
    def test_generate_api_key(self, db: Session) -> None:
        svc = UserService()
        api_key, raw_key = svc.generate_api_key(db, USER_ID, "test-key")
        assert api_key.user_id == USER_ID
        assert api_key.name == "test-key"
        assert api_key.is_active is True
        assert len(raw_key) > 0
        assert api_key.key_prefix == raw_key[:8]

    def test_list_api_keys(self, db: Session) -> None:
        svc = UserService()
        svc.generate_api_key(db, USER_ID, "k1")
        svc.generate_api_key(db, USER_ID, "k2")
        keys = svc.list_api_keys(db, USER_ID)
        assert len(keys) == 2

    def test_list_api_keys_empty(self, db: Session) -> None:
        svc = UserService()
        keys = svc.list_api_keys(db, USER_ID)
        assert keys == []

    def test_revoke_api_key(self, db: Session) -> None:
        svc = UserService()
        api_key, _ = svc.generate_api_key(db, USER_ID, "revoke-me")
        svc.revoke_api_key(db, api_key.id, USER_ID)

        keys = svc.list_api_keys(db, USER_ID)
        assert keys[0].is_active is False

    def test_revoke_api_key_not_found_raises(self, db: Session) -> None:
        svc = UserService()
        with pytest.raises(NotFoundException):
            svc.revoke_api_key(db, 9999, USER_ID)

    def test_revoke_api_key_wrong_user_raises(self, db: Session) -> None:
        svc = UserService()
        api_key, _ = svc.generate_api_key(db, USER_ID, "other-key")
        with pytest.raises(NotFoundException):
            svc.revoke_api_key(db, api_key.id, 9999)

    def test_validate_api_key_success(self, db: Session) -> None:
        svc = UserService()
        _, raw_key = svc.generate_api_key(db, USER_ID, "validate-me")
        result = svc.validate_api_key(db, raw_key)
        assert result is not None
        assert result.user_id == USER_ID
        assert result.last_used_at is not None

    def test_validate_api_key_invalid_returns_none(self, db: Session) -> None:
        svc = UserService()
        result = svc.validate_api_key(db, "nonexistent-key")
        assert result is None

    def test_validate_api_key_revoked_returns_none(self, db: Session) -> None:
        svc = UserService()
        api_key, raw_key = svc.generate_api_key(db, USER_ID, "revoked-key")
        svc.revoke_api_key(db, api_key.id, USER_ID)
        result = svc.validate_api_key(db, raw_key)
        assert result is None
