import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.exceptions import ConflictException, NotFoundException

from .models import UserApiKey, UserProfile, UserRole


class UserService:
    @staticmethod
    def create_profile(db: Session, user_id: int, data: dict) -> UserProfile:
        existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if existing:
            raise ConflictException(detail="Profile already exists for this user")

        profile = UserProfile(user_id=user_id, **data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def get_profile(db: Session, user_id: int) -> UserProfile:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise NotFoundException(detail="Profile not found")
        return profile

    @staticmethod
    def update_profile(db: Session, user_id: int, data: dict) -> UserProfile:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise NotFoundException(detail="Profile not found")

        for key, value in data.items():
            if value is not None:
                setattr(profile, key, value)

        profile.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile

    @staticmethod
    def delete_profile(db: Session, user_id: int) -> None:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            raise NotFoundException(detail="Profile not found")
        db.delete(profile)
        db.commit()

    @staticmethod
    def assign_role(db: Session, user_id: int, role: str) -> UserRole:
        existing = db.query(UserRole).filter(UserRole.user_id == user_id).first()
        if existing:
            existing.role = role
            db.commit()
            db.refresh(existing)
            return existing

        user_role = UserRole(user_id=user_id, role=role)
        db.add(user_role)
        db.commit()
        db.refresh(user_role)
        return user_role

    @staticmethod
    def get_user_role(db: Session, user_id: int) -> UserRole:
        role = db.query(UserRole).filter(UserRole.user_id == user_id).first()
        if not role:
            # Return a default "user" role without persisting
            return UserRole(id=None, user_id=user_id, role="user", created_at=datetime.now(timezone.utc))
        return role

    @staticmethod
    def generate_api_key(db: Session, user_id: int, name: str) -> tuple[UserApiKey, str]:
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]

        api_key = UserApiKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=name,
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key, raw_key

    @staticmethod
    def list_api_keys(db: Session, user_id: int) -> list[UserApiKey]:
        return db.query(UserApiKey).filter(UserApiKey.user_id == user_id).all()

    @staticmethod
    def revoke_api_key(db: Session, key_id: int, user_id: int) -> None:
        api_key = (
            db.query(UserApiKey)
            .filter(UserApiKey.id == key_id, UserApiKey.user_id == user_id)
            .first()
        )
        if not api_key:
            raise NotFoundException(detail="API key not found")
        api_key.is_active = False
        db.commit()

    @staticmethod
    def validate_api_key(db: Session, raw_key: str) -> UserApiKey | None:
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = (
            db.query(UserApiKey)
            .filter(UserApiKey.key_hash == key_hash, UserApiKey.is_active.is_(True))
            .first()
        )
        if api_key:
            api_key.last_used_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(api_key)
        return api_key
