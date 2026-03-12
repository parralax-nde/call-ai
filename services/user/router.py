from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import get_current_user
from shared.database import get_db
from shared.exceptions import ForbiddenException, UnauthorizedException

from .schemas import (
    AccountSettings,
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ProfileCreate,
    ProfileResponse,
    ProfileUpdate,
    RoleAssign,
    RoleResponse,
)
from .service import UserService

router = APIRouter(prefix="/users", tags=["Users"])
user_service = UserService()


def _get_user_id(current_user: dict) -> int:
    try:
        return int(current_user["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedException(detail="Invalid token: missing or invalid subject") from exc


def _require_admin(current_user: dict) -> None:
    if not current_user.get("is_admin", False):
        raise ForbiddenException(detail="Admin access required")


@router.post("/profile", response_model=ProfileResponse, status_code=201)
def create_profile(
    data: ProfileCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    user_id = _get_user_id(current_user)
    profile = user_service.create_profile(db, user_id, data.model_dump())
    return ProfileResponse.model_validate(profile)


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    user_id = _get_user_id(current_user)
    profile = user_service.get_profile(db, user_id)
    return ProfileResponse.model_validate(profile)


@router.put("/profile", response_model=ProfileResponse)
def update_profile(
    data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    user_id = _get_user_id(current_user)
    profile = user_service.update_profile(db, user_id, data.model_dump(exclude_unset=True))
    return ProfileResponse.model_validate(profile)


@router.delete("/profile", status_code=204)
def delete_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    user_id = _get_user_id(current_user)
    user_service.delete_profile(db, user_id)


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_user_profile(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    _require_admin(current_user)
    profile = user_service.get_profile(db, user_id)
    return ProfileResponse.model_validate(profile)


@router.post("/roles", response_model=RoleResponse, status_code=201)
def assign_role(
    data: RoleAssign,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleResponse:
    _require_admin(current_user)
    role = user_service.assign_role(db, data.user_id, data.role)
    return RoleResponse.model_validate(role)


@router.get("/roles/{user_id}", response_model=RoleResponse)
def get_user_role(
    user_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoleResponse:
    role = user_service.get_user_role(db, user_id)
    return RoleResponse.model_validate(role)


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=201)
def generate_api_key(
    data: ApiKeyCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApiKeyCreatedResponse:
    user_id = _get_user_id(current_user)
    api_key, raw_key = user_service.generate_api_key(db, user_id, data.name)
    response = ApiKeyCreatedResponse.model_validate(api_key)
    response.api_key = raw_key
    return response


@router.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ApiKeyResponse]:
    user_id = _get_user_id(current_user)
    keys = user_service.list_api_keys(db, user_id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.delete("/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    user_id = _get_user_id(current_user)
    user_service.revoke_api_key(db, key_id, user_id)


@router.put("/settings", response_model=ProfileResponse)
def update_settings(
    data: AccountSettings,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProfileResponse:
    user_id = _get_user_id(current_user)
    profile = user_service.update_profile(db, user_id, data.model_dump(exclude_unset=True))
    return ProfileResponse.model_validate(profile)
