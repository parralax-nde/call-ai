"""Comprehensive tests for the AI Assistant Config Service."""

from collections.abc import Generator

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import Session, sessionmaker

from services.ai_config.models import (
    AiPersona,
    ConversationalFlow,
    PromptTemplate,
    PromptVersion,
)
from services.ai_config.router import router as ai_config_router
from services.ai_config.schemas import (
    FlowCreate,
    FlowUpdate,
    PersonaCreate,
    PersonaUpdate,
    PromptCreate,
    PromptUpdate,
)
from services.ai_config.service import AiConfigService
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

    app.include_router(ai_config_router)

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
def created_prompt(client: TestClient, auth_headers: dict) -> dict:
    payload = {"name": "Greeting Prompt", "content": "Hello, how can I help you?"}
    resp = client.post("/ai-config/prompts", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def created_persona(client: TestClient, auth_headers: dict) -> dict:
    payload = {
        "name": "Friendly Bot",
        "description": "A helpful assistant",
        "tone": "friendly",
        "traits": ["helpful", "patient"],
    }
    resp = client.post("/ai-config/personas", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


@pytest.fixture
def created_flow(client: TestClient, auth_headers: dict) -> dict:
    payload = {
        "name": "Onboarding Flow",
        "flow_config": {"steps": [{"action": "greet"}, {"action": "ask_name"}]},
    }
    resp = client.post("/ai-config/flows", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


# ===================================================================
# 1. Prompt Templates
# ===================================================================
class TestPromptTemplates:
    def test_create_prompt(self, client: TestClient, auth_headers: dict) -> None:
        payload = {"name": "Test Prompt", "content": "Say hello"}
        resp = client.post("/ai-config/prompts", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test Prompt"
        assert data["content"] == "Say hello"
        assert data["version"] == 1
        assert data["is_active"] is True
        assert data["user_id"] == TEST_USER_ID

    def test_get_prompt(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        pid = created_prompt["id"]
        resp = client.get(f"/ai-config/prompts/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    def test_list_prompts(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        resp = client.get("/ai-config/prompts", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_update_prompt(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        pid = created_prompt["id"]
        resp = client.put(
            f"/ai-config/prompts/{pid}",
            json={"name": "Updated Prompt"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Prompt"

    def test_delete_prompt(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        pid = created_prompt["id"]
        resp = client.delete(f"/ai-config/prompts/{pid}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/ai-config/prompts/{pid}", headers=auth_headers)
        assert resp.status_code == 404

    def test_prompt_not_found(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        resp = client.get("/ai-config/prompts/99999", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 2. Prompt Versioning
# ===================================================================
class TestPromptVersioning:
    def test_update_content_creates_new_version(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        pid = created_prompt["id"]
        resp = client.put(
            f"/ai-config/prompts/{pid}",
            json={"content": "Updated content v2"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version"] == 2

    def test_get_versions(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        pid = created_prompt["id"]
        # Create a second version
        client.put(
            f"/ai-config/prompts/{pid}",
            json={"content": "Version two content"},
            headers=auth_headers,
        )
        resp = client.get(
            f"/ai-config/prompts/{pid}/versions", headers=auth_headers
        )
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) == 2
        # Ordered desc by version
        assert versions[0]["version"] > versions[1]["version"]

    def test_revert_to_version(
        self, client: TestClient, auth_headers: dict, created_prompt: dict
    ) -> None:
        pid = created_prompt["id"]
        original_content = created_prompt["content"]

        # Create v2
        client.put(
            f"/ai-config/prompts/{pid}",
            json={"content": "Changed content"},
            headers=auth_headers,
        )

        # Revert to v1
        resp = client.post(
            f"/ai-config/prompts/{pid}/revert/1", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == original_content
        assert data["version"] == 3  # revert creates a new version


# ===================================================================
# 3. AI Personas
# ===================================================================
class TestAiPersonas:
    def test_create_persona(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        payload = {
            "name": "Sales Bot",
            "description": "Sells products",
            "tone": "persuasive",
            "traits": ["confident", "knowledgeable"],
        }
        resp = client.post("/ai-config/personas", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Sales Bot"
        assert data["tone"] == "persuasive"
        assert data["traits"] == ["confident", "knowledgeable"]

    def test_get_persona(
        self, client: TestClient, auth_headers: dict, created_persona: dict
    ) -> None:
        pid = created_persona["id"]
        resp = client.get(f"/ai-config/personas/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == created_persona["name"]

    def test_list_personas(
        self, client: TestClient, auth_headers: dict, created_persona: dict
    ) -> None:
        resp = client.get("/ai-config/personas", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_persona(
        self, client: TestClient, auth_headers: dict, created_persona: dict
    ) -> None:
        pid = created_persona["id"]
        resp = client.put(
            f"/ai-config/personas/{pid}",
            json={"tone": "casual"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["tone"] == "casual"

    def test_delete_persona(
        self, client: TestClient, auth_headers: dict, created_persona: dict
    ) -> None:
        pid = created_persona["id"]
        resp = client.delete(f"/ai-config/personas/{pid}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/ai-config/personas/{pid}", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 4. Conversational Flows
# ===================================================================
class TestConversationalFlows:
    def test_create_flow(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        payload = {
            "name": "Support Flow",
            "flow_config": {"steps": [{"action": "ask_issue"}]},
        }
        resp = client.post("/ai-config/flows", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Support Flow"
        assert data["flow_config"]["steps"][0]["action"] == "ask_issue"

    def test_get_flow(
        self, client: TestClient, auth_headers: dict, created_flow: dict
    ) -> None:
        fid = created_flow["id"]
        resp = client.get(f"/ai-config/flows/{fid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == created_flow["name"]

    def test_list_flows(
        self, client: TestClient, auth_headers: dict, created_flow: dict
    ) -> None:
        resp = client.get("/ai-config/flows", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_flow(
        self, client: TestClient, auth_headers: dict, created_flow: dict
    ) -> None:
        fid = created_flow["id"]
        resp = client.put(
            f"/ai-config/flows/{fid}",
            json={"name": "Updated Flow"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Flow"

    def test_delete_flow(
        self, client: TestClient, auth_headers: dict, created_flow: dict
    ) -> None:
        fid = created_flow["id"]
        resp = client.delete(f"/ai-config/flows/{fid}", headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get(f"/ai-config/flows/{fid}", headers=auth_headers)
        assert resp.status_code == 404


# ===================================================================
# 5. Service Layer Tests
# ===================================================================
class TestAiConfigServiceLayer:
    # --- Prompts ---
    def test_create_prompt(self, db: Session) -> None:
        svc = AiConfigService()
        prompt = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="P1", content="Hello")
        )
        assert prompt.id is not None
        assert prompt.name == "P1"
        assert prompt.version == 1

    def test_get_prompt(self, db: Session) -> None:
        svc = AiConfigService()
        created = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="P2", content="Hi")
        )
        found = svc.get_prompt(db, created.id)
        assert found.id == created.id

    def test_get_prompt_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        with pytest.raises(NotFoundException):
            svc.get_prompt(db, 999)

    def test_list_prompts(self, db: Session) -> None:
        svc = AiConfigService()
        svc.create_prompt(db, TEST_USER_ID, PromptCreate(name="A", content="a"))
        svc.create_prompt(db, TEST_USER_ID, PromptCreate(name="B", content="b"))
        results = svc.list_prompts(db, TEST_USER_ID)
        assert len(results) == 2

    def test_update_prompt_with_content(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="V", content="v1")
        )
        updated = svc.update_prompt(
            db, p.id, TEST_USER_ID, PromptUpdate(content="v2")
        )
        assert updated.version == 2
        assert updated.content == "v2"

    def test_update_prompt_without_content(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="V", content="v1")
        )
        updated = svc.update_prompt(
            db, p.id, TEST_USER_ID, PromptUpdate(name="New Name")
        )
        assert updated.version == 1  # no version bump
        assert updated.name == "New Name"

    def test_delete_prompt(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="Del", content="bye")
        )
        svc.delete_prompt(db, p.id)
        with pytest.raises(NotFoundException):
            svc.get_prompt(db, p.id)

    def test_delete_prompt_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        with pytest.raises(NotFoundException):
            svc.delete_prompt(db, 999)

    # --- Versions ---
    def test_get_prompt_versions(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="VP", content="c1")
        )
        svc.update_prompt(db, p.id, TEST_USER_ID, PromptUpdate(content="c2"))
        versions = svc.get_prompt_versions(db, p.id)
        assert len(versions) == 2

    def test_revert_prompt_to_version(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="RV", content="original")
        )
        svc.update_prompt(db, p.id, TEST_USER_ID, PromptUpdate(content="changed"))
        reverted = svc.revert_prompt_to_version(db, p.id, 1)
        assert reverted.content == "original"
        assert reverted.version == 3

    def test_revert_version_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_prompt(
            db, TEST_USER_ID, PromptCreate(name="RV2", content="x")
        )
        with pytest.raises(NotFoundException):
            svc.revert_prompt_to_version(db, p.id, 99)

    # --- Personas ---
    def test_create_persona(self, db: Session) -> None:
        svc = AiConfigService()
        persona = svc.create_persona(
            db, TEST_USER_ID,
            PersonaCreate(name="Bot", tone="formal", traits=["polite"]),
        )
        assert persona.id is not None
        assert persona.name == "Bot"

    def test_get_persona(self, db: Session) -> None:
        svc = AiConfigService()
        created = svc.create_persona(
            db, TEST_USER_ID, PersonaCreate(name="G", tone="calm")
        )
        found = svc.get_persona(db, created.id)
        assert found.id == created.id

    def test_get_persona_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        with pytest.raises(NotFoundException):
            svc.get_persona(db, 999)

    def test_list_personas(self, db: Session) -> None:
        svc = AiConfigService()
        svc.create_persona(db, TEST_USER_ID, PersonaCreate(name="A"))
        svc.create_persona(db, TEST_USER_ID, PersonaCreate(name="B"))
        results = svc.list_personas(db, TEST_USER_ID)
        assert len(results) == 2

    def test_update_persona(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_persona(
            db, TEST_USER_ID, PersonaCreate(name="Up", tone="formal")
        )
        updated = svc.update_persona(db, p.id, PersonaUpdate(tone="casual"))
        assert updated.tone == "casual"

    def test_delete_persona(self, db: Session) -> None:
        svc = AiConfigService()
        p = svc.create_persona(
            db, TEST_USER_ID, PersonaCreate(name="Del")
        )
        svc.delete_persona(db, p.id)
        with pytest.raises(NotFoundException):
            svc.get_persona(db, p.id)

    def test_delete_persona_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        with pytest.raises(NotFoundException):
            svc.delete_persona(db, 999)

    # --- Flows ---
    def test_create_flow(self, db: Session) -> None:
        svc = AiConfigService()
        flow = svc.create_flow(
            db, TEST_USER_ID,
            FlowCreate(name="F1", flow_config={"steps": []}),
        )
        assert flow.id is not None
        assert flow.name == "F1"

    def test_get_flow(self, db: Session) -> None:
        svc = AiConfigService()
        created = svc.create_flow(
            db, TEST_USER_ID, FlowCreate(name="G", flow_config={"a": 1})
        )
        found = svc.get_flow(db, created.id)
        assert found.id == created.id

    def test_get_flow_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        with pytest.raises(NotFoundException):
            svc.get_flow(db, 999)

    def test_list_flows(self, db: Session) -> None:
        svc = AiConfigService()
        svc.create_flow(
            db, TEST_USER_ID, FlowCreate(name="A", flow_config={})
        )
        svc.create_flow(
            db, TEST_USER_ID, FlowCreate(name="B", flow_config={})
        )
        results = svc.list_flows(db, TEST_USER_ID)
        assert len(results) == 2

    def test_update_flow(self, db: Session) -> None:
        svc = AiConfigService()
        f = svc.create_flow(
            db, TEST_USER_ID, FlowCreate(name="UF", flow_config={"x": 1})
        )
        updated = svc.update_flow(db, f.id, FlowUpdate(name="Updated"))
        assert updated.name == "Updated"

    def test_delete_flow(self, db: Session) -> None:
        svc = AiConfigService()
        f = svc.create_flow(
            db, TEST_USER_ID, FlowCreate(name="DF", flow_config={})
        )
        svc.delete_flow(db, f.id)
        with pytest.raises(NotFoundException):
            svc.get_flow(db, f.id)

    def test_delete_flow_not_found(self, db: Session) -> None:
        svc = AiConfigService()
        with pytest.raises(NotFoundException):
            svc.delete_flow(db, 999)
