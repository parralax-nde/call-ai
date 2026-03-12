from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db

from .schemas import (
    FlowCreate,
    FlowResponse,
    FlowUpdate,
    PersonaCreate,
    PersonaResponse,
    PersonaUpdate,
    PromptCreate,
    PromptResponse,
    PromptUpdate,
    VersionResponse,
)
from .service import AiConfigService

router = APIRouter(prefix="/ai-config", tags=["AI Assistant Configuration"])


# --- Prompt Endpoints ---


@router.post("/prompts", response_model=PromptResponse, status_code=201)
def create_prompt(
    data: PromptCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PromptResponse:
    prompt = AiConfigService.create_prompt(db, int(current_user["sub"]), data)
    return PromptResponse.model_validate(prompt)


@router.get("/prompts/{prompt_id}", response_model=PromptResponse)
def get_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PromptResponse:
    prompt = AiConfigService.get_prompt(db, prompt_id)
    return PromptResponse.model_validate(prompt)


@router.get("/prompts", response_model=list[PromptResponse])
def list_prompts(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PromptResponse]:
    prompts = AiConfigService.list_prompts(db, int(current_user["sub"]), skip, limit)
    return [PromptResponse.model_validate(p) for p in prompts]


@router.put("/prompts/{prompt_id}", response_model=PromptResponse)
def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PromptResponse:
    prompt = AiConfigService.update_prompt(
        db, prompt_id, int(current_user["sub"]), data
    )
    return PromptResponse.model_validate(prompt)


@router.delete("/prompts/{prompt_id}", status_code=204)
def delete_prompt(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    AiConfigService.delete_prompt(db, prompt_id)


# --- Persona Endpoints ---


@router.post("/personas", response_model=PersonaResponse, status_code=201)
def create_persona(
    data: PersonaCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PersonaResponse:
    persona = AiConfigService.create_persona(db, int(current_user["sub"]), data)
    return PersonaResponse.model_validate(persona)


@router.get("/personas/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PersonaResponse:
    persona = AiConfigService.get_persona(db, persona_id)
    return PersonaResponse.model_validate(persona)


@router.get("/personas", response_model=list[PersonaResponse])
def list_personas(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[PersonaResponse]:
    personas = AiConfigService.list_personas(db, int(current_user["sub"]), skip, limit)
    return [PersonaResponse.model_validate(p) for p in personas]


@router.put("/personas/{persona_id}", response_model=PersonaResponse)
def update_persona(
    persona_id: int,
    data: PersonaUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PersonaResponse:
    persona = AiConfigService.update_persona(db, persona_id, data)
    return PersonaResponse.model_validate(persona)


@router.delete("/personas/{persona_id}", status_code=204)
def delete_persona(
    persona_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    AiConfigService.delete_persona(db, persona_id)


# --- Flow Endpoints ---


@router.post("/flows", response_model=FlowResponse, status_code=201)
def create_flow(
    data: FlowCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FlowResponse:
    flow = AiConfigService.create_flow(db, int(current_user["sub"]), data)
    return FlowResponse.model_validate(flow)


@router.get("/flows/{flow_id}", response_model=FlowResponse)
def get_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FlowResponse:
    flow = AiConfigService.get_flow(db, flow_id)
    return FlowResponse.model_validate(flow)


@router.get("/flows", response_model=list[FlowResponse])
def list_flows(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[FlowResponse]:
    flows = AiConfigService.list_flows(db, int(current_user["sub"]), skip, limit)
    return [FlowResponse.model_validate(f) for f in flows]


@router.put("/flows/{flow_id}", response_model=FlowResponse)
def update_flow(
    flow_id: int,
    data: FlowUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> FlowResponse:
    flow = AiConfigService.update_flow(db, flow_id, data)
    return FlowResponse.model_validate(flow)


@router.delete("/flows/{flow_id}", status_code=204)
def delete_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    AiConfigService.delete_flow(db, flow_id)


# --- Version History Endpoints ---


@router.get("/prompts/{prompt_id}/versions", response_model=list[VersionResponse])
def get_prompt_versions(
    prompt_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[VersionResponse]:
    versions = AiConfigService.get_prompt_versions(db, prompt_id)
    return [VersionResponse.model_validate(v) for v in versions]


@router.post("/prompts/{prompt_id}/revert/{version}", response_model=PromptResponse)
def revert_prompt_to_version(
    prompt_id: int,
    version: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PromptResponse:
    prompt = AiConfigService.revert_prompt_to_version(db, prompt_id, version)
    return PromptResponse.model_validate(prompt)
