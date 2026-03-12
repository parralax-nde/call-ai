import json

from sqlalchemy.orm import Session

from shared.exceptions import NotFoundException

from .models import AiPersona, ConversationalFlow, PromptTemplate, PromptVersion
from .schemas import (
    FlowCreate,
    FlowUpdate,
    PersonaCreate,
    PersonaUpdate,
    PromptCreate,
    PromptUpdate,
)


class AiConfigService:
    # --- Prompt CRUD ---

    @staticmethod
    def create_prompt(db: Session, user_id: int, data: PromptCreate) -> PromptTemplate:
        prompt = PromptTemplate(
            user_id=user_id,
            name=data.name,
            content=data.content,
            persona_id=data.persona_id,
        )
        db.add(prompt)
        db.commit()
        db.refresh(prompt)

        version = PromptVersion(
            prompt_template_id=prompt.id,
            version=1,
            content=prompt.content,
            created_by=user_id,
        )
        db.add(version)
        db.commit()
        return prompt

    @staticmethod
    def get_prompt(db: Session, prompt_id: int) -> PromptTemplate:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            raise NotFoundException(detail="Prompt template not found")
        return prompt

    @staticmethod
    def list_prompts(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[PromptTemplate]:
        return (
            db.query(PromptTemplate)
            .filter(PromptTemplate.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_prompt(
        db: Session, prompt_id: int, user_id: int, data: PromptUpdate
    ) -> PromptTemplate:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            raise NotFoundException(detail="Prompt template not found")

        update_data = data.model_dump(exclude_unset=True)
        content_changed = "content" in update_data and update_data["content"] != prompt.content

        for field, value in update_data.items():
            setattr(prompt, field, value)

        if content_changed:
            prompt.version += 1
            version = PromptVersion(
                prompt_template_id=prompt.id,
                version=prompt.version,
                content=prompt.content,
                created_by=user_id,
            )
            db.add(version)

        db.commit()
        db.refresh(prompt)
        return prompt

    @staticmethod
    def delete_prompt(db: Session, prompt_id: int) -> None:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            raise NotFoundException(detail="Prompt template not found")
        db.delete(prompt)
        db.commit()

    # --- Persona CRUD ---

    @staticmethod
    def create_persona(db: Session, user_id: int, data: PersonaCreate) -> AiPersona:
        traits_json = json.dumps(data.traits) if data.traits is not None else None
        persona = AiPersona(
            user_id=user_id,
            name=data.name,
            description=data.description,
            tone=data.tone,
            traits=traits_json,
        )
        db.add(persona)
        db.commit()
        db.refresh(persona)
        return persona

    @staticmethod
    def get_persona(db: Session, persona_id: int) -> AiPersona:
        persona = db.query(AiPersona).filter(AiPersona.id == persona_id).first()
        if not persona:
            raise NotFoundException(detail="AI persona not found")
        return persona

    @staticmethod
    def list_personas(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[AiPersona]:
        return (
            db.query(AiPersona)
            .filter(AiPersona.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_persona(
        db: Session, persona_id: int, data: PersonaUpdate
    ) -> AiPersona:
        persona = db.query(AiPersona).filter(AiPersona.id == persona_id).first()
        if not persona:
            raise NotFoundException(detail="AI persona not found")

        update_data = data.model_dump(exclude_unset=True)
        if "traits" in update_data:
            update_data["traits"] = (
                json.dumps(update_data["traits"])
                if update_data["traits"] is not None
                else None
            )

        for field, value in update_data.items():
            setattr(persona, field, value)

        db.commit()
        db.refresh(persona)
        return persona

    @staticmethod
    def delete_persona(db: Session, persona_id: int) -> None:
        persona = db.query(AiPersona).filter(AiPersona.id == persona_id).first()
        if not persona:
            raise NotFoundException(detail="AI persona not found")
        db.delete(persona)
        db.commit()

    # --- Flow CRUD ---

    @staticmethod
    def create_flow(db: Session, user_id: int, data: FlowCreate) -> ConversationalFlow:
        flow = ConversationalFlow(
            user_id=user_id,
            name=data.name,
            flow_config=json.dumps(data.flow_config),
            prompt_template_id=data.prompt_template_id,
        )
        db.add(flow)
        db.commit()
        db.refresh(flow)
        return flow

    @staticmethod
    def get_flow(db: Session, flow_id: int) -> ConversationalFlow:
        flow = db.query(ConversationalFlow).filter(ConversationalFlow.id == flow_id).first()
        if not flow:
            raise NotFoundException(detail="Conversational flow not found")
        return flow

    @staticmethod
    def list_flows(
        db: Session, user_id: int, skip: int = 0, limit: int = 20
    ) -> list[ConversationalFlow]:
        return (
            db.query(ConversationalFlow)
            .filter(ConversationalFlow.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def update_flow(
        db: Session, flow_id: int, data: FlowUpdate
    ) -> ConversationalFlow:
        flow = db.query(ConversationalFlow).filter(ConversationalFlow.id == flow_id).first()
        if not flow:
            raise NotFoundException(detail="Conversational flow not found")

        update_data = data.model_dump(exclude_unset=True)
        if "flow_config" in update_data:
            update_data["flow_config"] = json.dumps(update_data["flow_config"])

        for field, value in update_data.items():
            setattr(flow, field, value)

        db.commit()
        db.refresh(flow)
        return flow

    @staticmethod
    def delete_flow(db: Session, flow_id: int) -> None:
        flow = db.query(ConversationalFlow).filter(ConversationalFlow.id == flow_id).first()
        if not flow:
            raise NotFoundException(detail="Conversational flow not found")
        db.delete(flow)
        db.commit()

    # --- Version History ---

    @staticmethod
    def get_prompt_versions(db: Session, prompt_id: int) -> list[PromptVersion]:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            raise NotFoundException(detail="Prompt template not found")
        return (
            db.query(PromptVersion)
            .filter(PromptVersion.prompt_template_id == prompt_id)
            .order_by(PromptVersion.version.desc())
            .all()
        )

    @staticmethod
    def revert_prompt_to_version(
        db: Session, prompt_id: int, version: int
    ) -> PromptTemplate:
        prompt = db.query(PromptTemplate).filter(PromptTemplate.id == prompt_id).first()
        if not prompt:
            raise NotFoundException(detail="Prompt template not found")

        version_record = (
            db.query(PromptVersion)
            .filter(
                PromptVersion.prompt_template_id == prompt_id,
                PromptVersion.version == version,
            )
            .first()
        )
        if not version_record:
            raise NotFoundException(detail=f"Version {version} not found")

        prompt.version += 1
        prompt.content = version_record.content

        revert_version = PromptVersion(
            prompt_template_id=prompt.id,
            version=prompt.version,
            content=version_record.content,
            created_by=prompt.user_id,
        )
        db.add(revert_version)
        db.commit()
        db.refresh(prompt)
        return prompt
