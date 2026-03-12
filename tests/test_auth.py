"""Comprehensive tests for the Auth Service."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.auth.models import BlacklistedToken, User
from services.auth.router import router as auth_router
from services.auth.service import AuthService
from shared.auth import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from shared.database import Base, get_db
from shared.exceptions import (
    AppException,
    BadRequestException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
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


def _build_test_app() -> FastAPI:
    """Create a FastAPI app wired to the test DB."""
    app = FastAPI()

    # Must register the same exception handler used in production
    @app.exception_handler(AppException)
    async def _handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    app.include_router(auth_router)

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
def registered_user(client: TestClient) -> dict:
    """Register a user and return the registration payload + response."""
    payload = {"email": "user@example.com", "password": "securepassword1"}
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    return {**payload, "response": resp.json()}


@pytest.fixture
def auth_token(registered_user: dict, client: TestClient) -> str:
    """Login the registered user and return the bearer token."""
    resp = client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


# ===================================================================
# 1. User Registration
# ===================================================================
class TestUserRegistration:
    def test_successful_registration(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/register",
            json={"email": "new@example.com", "password": "strongpass1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["is_active"] is True
        assert data["is_admin"] is False
        assert "id" in data
        assert "created_at" in data

    def test_duplicate_email_returns_409(self, client: TestClient) -> None:
        payload = {"email": "dup@example.com", "password": "strongpass1"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    def test_invalid_email_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "strongpass1"},
        )
        assert resp.status_code == 422

    def test_short_password_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/register",
            json={"email": "valid@example.com", "password": "short"},
        )
        assert resp.status_code == 422


# ===================================================================
# 2. User Login
# ===================================================================
class TestUserLogin:
    def test_successful_login(
        self, client: TestClient, registered_user: dict
    ) -> None:
        resp = client.post(
            "/auth/login",
            json={
                "email": registered_user["email"],
                "password": registered_user["password"],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_wrong_password_returns_401(
        self, client: TestClient, registered_user: dict
    ) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": registered_user["email"], "password": "wrongpassword1"},
        )
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_nonexistent_email_returns_401(self, client: TestClient) -> None:
        resp = client.post(
            "/auth/login",
            json={"email": "ghost@example.com", "password": "anypassword1"},
        )
        assert resp.status_code == 401


# ===================================================================
# 3. Token Management
# ===================================================================
class TestTokenManagement:
    def test_token_refresh_returns_new_token(
        self, client: TestClient, auth_token: str, auth_headers: dict
    ) -> None:
        resp = client.post("/auth/refresh", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # New token should differ from the original
        assert data["access_token"] != auth_token

    def test_logout_returns_success(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.post("/auth/logout", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Successfully logged out"

    def test_blacklisted_token_is_rejected_service_layer(self, db: Session) -> None:
        svc = AuthService()
        token = "some-jwt-token-value"

        assert svc.is_token_blacklisted(db, token) is False
        svc.blacklist_token(db, token)
        assert svc.is_token_blacklisted(db, token) is True

    def test_refresh_with_no_token_returns_401(self, client: TestClient) -> None:
        resp = client.post("/auth/refresh")
        assert resp.status_code in (401, 403)

    def test_logout_with_no_token_returns_401(self, client: TestClient) -> None:
        resp = client.post("/auth/logout")
        assert resp.status_code in (401, 403)


# ===================================================================
# 4. Google OAuth
# ===================================================================
class TestGoogleOAuth:
    def test_google_login_creates_new_user(self, client: TestClient) -> None:
        resp = client.post("/auth/google", json={"token": "google-user-123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_google_login_returns_existing_user(self, client: TestClient) -> None:
        # First call creates the user
        resp1 = client.post("/auth/google", json={"token": "google-user-456"})
        assert resp1.status_code == 200
        token1 = resp1.json()["access_token"]

        # Second call with same google token should return the same user
        resp2 = client.post("/auth/google", json={"token": "google-user-456"})
        assert resp2.status_code == 200

        # Verify both tokens decode to the same user (same "sub")
        payload1 = verify_token(token1)
        payload2 = verify_token(resp2.json()["access_token"])
        assert payload1["sub"] == payload2["sub"]

    def test_google_login_links_existing_email_user(
        self, client: TestClient
    ) -> None:
        """If a user registered by email already exists, Google login links
        the google_id and returns the same user."""
        email = "google-user-789@gmail.com"
        client.post(
            "/auth/register", json={"email": email, "password": "password1234"}
        )

        resp = client.post("/auth/google", json={"token": "google-user-789"})
        assert resp.status_code == 200
        payload = verify_token(resp.json()["access_token"])
        assert payload["email"] == email


# ===================================================================
# 5. Password Reset
# ===================================================================
class TestPasswordReset:
    def test_request_password_reset(
        self, client: TestClient, registered_user: dict
    ) -> None:
        resp = client.post(
            "/auth/password-reset",
            json={"email": registered_user["email"]},
        )
        assert resp.status_code == 200
        assert "sent" in resp.json()["message"].lower()

    def test_request_reset_nonexistent_email_returns_404(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/auth/password-reset", json={"email": "nobody@example.com"}
        )
        assert resp.status_code == 404

    def test_confirm_password_reset(
        self, client: TestClient, registered_user: dict, db: Session
    ) -> None:
        # Create reset token via service layer
        svc = AuthService()
        reset_token = svc.create_password_reset_token(
            db, registered_user["email"]
        )

        new_password = "mynewpassword1"
        resp = client.post(
            "/auth/password-reset/confirm",
            json={"token": reset_token, "new_password": new_password},
        )
        assert resp.status_code == 200
        assert "reset" in resp.json()["message"].lower()

        # Verify the new password works for login
        resp = client.post(
            "/auth/login",
            json={
                "email": registered_user["email"],
                "password": new_password,
            },
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_confirm_reset_invalid_token_returns_400(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/auth/password-reset/confirm",
            json={"token": "bogus-token", "new_password": "newpassword1"},
        )
        assert resp.status_code == 400

    def test_confirm_reset_short_password_returns_422(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/auth/password-reset/confirm",
            json={"token": "any-token", "new_password": "short"},
        )
        assert resp.status_code == 422


# ===================================================================
# 6. Auth Utilities (shared/auth.py)
# ===================================================================
class TestAuthUtilities:
    def test_create_access_token_creates_valid_token(self) -> None:
        token = create_access_token(data={"sub": "42", "email": "a@b.com"})
        assert isinstance(token, str)
        payload = verify_token(token)
        assert payload["sub"] == "42"
        assert payload["email"] == "a@b.com"
        assert "exp" in payload

    def test_verify_token_succeeds_with_valid_token(self) -> None:
        token = create_access_token(data={"sub": "1"})
        payload = verify_token(token)
        assert payload["sub"] == "1"

    def test_verify_token_fails_with_invalid_token(self) -> None:
        with pytest.raises(UnauthorizedException):
            verify_token("this.is.not.a.valid.jwt")

    def test_verify_token_fails_without_subject(self) -> None:
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from shared.config import get_settings

        settings = get_settings()
        bad_token = jwt.encode(
            {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
            settings.SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        with pytest.raises(UnauthorizedException, match="missing subject"):
            verify_token(bad_token)

    def test_password_hashing_and_verification(self) -> None:
        plain = "my_secret_password"
        hashed = get_password_hash(plain)
        assert hashed != plain
        assert verify_password(plain, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_password_hash_is_unique_per_call(self) -> None:
        plain = "samepassword"
        h1 = get_password_hash(plain)
        h2 = get_password_hash(plain)
        # bcrypt produces different salts each time
        assert h1 != h2
        assert verify_password(plain, h1) is True
        assert verify_password(plain, h2) is True


# ===================================================================
# 7. Service-layer unit tests
# ===================================================================
class TestAuthServiceLayer:
    def test_register_user(self, db: Session) -> None:
        svc = AuthService()
        user = svc.register_user(db, "svc@test.com", "password1234")
        assert user.email == "svc@test.com"
        assert user.is_active is True
        assert user.id is not None

    def test_register_duplicate_raises_conflict(self, db: Session) -> None:
        svc = AuthService()
        svc.register_user(db, "dup@test.com", "password1234")
        with pytest.raises(ConflictException):
            svc.register_user(db, "dup@test.com", "password1234")

    def test_authenticate_user_success(self, db: Session) -> None:
        svc = AuthService()
        svc.register_user(db, "auth@test.com", "password1234")
        user = svc.authenticate_user(db, "auth@test.com", "password1234")
        assert user is not None
        assert user.email == "auth@test.com"

    def test_authenticate_user_wrong_password(self, db: Session) -> None:
        svc = AuthService()
        svc.register_user(db, "auth2@test.com", "password1234")
        assert svc.authenticate_user(db, "auth2@test.com", "wrong") is None

    def test_authenticate_user_no_such_email(self, db: Session) -> None:
        svc = AuthService()
        assert svc.authenticate_user(db, "nope@test.com", "pass") is None

    def test_get_or_create_google_user_creates(self, db: Session) -> None:
        svc = AuthService()
        user = svc.get_or_create_google_user(db, "g123", "g123@gmail.com")
        assert user.google_id == "g123"
        assert user.email == "g123@gmail.com"

    def test_get_or_create_google_user_returns_existing(
        self, db: Session
    ) -> None:
        svc = AuthService()
        u1 = svc.get_or_create_google_user(db, "g456", "g456@gmail.com")
        u2 = svc.get_or_create_google_user(db, "g456", "g456@gmail.com")
        assert u1.id == u2.id

    def test_create_password_reset_token(self, db: Session) -> None:
        svc = AuthService()
        svc.register_user(db, "reset@test.com", "password1234")
        token = svc.create_password_reset_token(db, "reset@test.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_password_reset_token_unknown_email(
        self, db: Session
    ) -> None:
        svc = AuthService()
        with pytest.raises(NotFoundException):
            svc.create_password_reset_token(db, "unknown@test.com")

    def test_reset_password_success(self, db: Session) -> None:
        svc = AuthService()
        svc.register_user(db, "rp@test.com", "oldpassword1")
        token = svc.create_password_reset_token(db, "rp@test.com")
        svc.reset_password(db, token, "newpassword1")

        # Old password must no longer work; new one must
        assert svc.authenticate_user(db, "rp@test.com", "oldpassword1") is None
        assert svc.authenticate_user(db, "rp@test.com", "newpassword1") is not None

    def test_reset_password_invalid_token(self, db: Session) -> None:
        svc = AuthService()
        with pytest.raises(BadRequestException):
            svc.reset_password(db, "invalid-token", "newpassword1")

    def test_reset_password_empty_token(self, db: Session) -> None:
        svc = AuthService()
        with pytest.raises(BadRequestException):
            svc.reset_password(db, "", "newpassword1")


# ===================================================================
# 8. Schema / Dependency Validation
# ===================================================================
class TestSchemaEmailValidation:
    """Verify that email-validator is installed and EmailStr works."""

    def test_email_str_schema_can_be_instantiated(self) -> None:
        from services.auth.schemas import UserRegister

        user = UserRegister(email="valid@example.com", password="securepass1")
        assert user.email == "valid@example.com"

    def test_email_str_rejects_invalid_email(self) -> None:
        from pydantic import ValidationError

        from services.auth.schemas import UserRegister

        with pytest.raises(ValidationError):
            UserRegister(email="not-valid", password="securepass1")
