import hashlib
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.exceptions import ConflictException, NotFoundException

from .models import UserApiKey, UserContact, UserOwnedNumber, UserProfile, UserRole


class UserService:
    MARKETPLACE_NUMBERS = [
        "+12065550101",
        "+12065550102",
        "+12065550103",
        "+12065550104",
        "+12065550105",
        "+12065550106",
    ]

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

    @classmethod
    def list_marketplace_numbers(cls, db: Session) -> list[dict]:
        owned_numbers = {
            n.phone_number
            for n in db.query(UserOwnedNumber.phone_number).all()
        }
        return [
            {"phone_number": n, "monthly_price_usd": 1.0}
            for n in cls.MARKETPLACE_NUMBERS
            if n not in owned_numbers
        ]

    @staticmethod
    def list_owned_numbers(db: Session, user_id: int) -> list[UserOwnedNumber]:
        return (
            db.query(UserOwnedNumber)
            .filter(UserOwnedNumber.user_id == user_id)
            .order_by(UserOwnedNumber.purchased_at.desc())
            .all()
        )

    @classmethod
    def purchase_number(
        cls, db: Session, user_id: int, phone_number: str
    ) -> UserOwnedNumber:
        if phone_number not in cls.MARKETPLACE_NUMBERS:
            raise NotFoundException(detail="Phone number is not available in marketplace")

        existing = (
            db.query(UserOwnedNumber)
            .filter(UserOwnedNumber.phone_number == phone_number)
            .first()
        )
        if existing:
            raise ConflictException(detail="Phone number already purchased")

        owned = UserOwnedNumber(
            user_id=user_id,
            phone_number=phone_number,
            monthly_price_usd=1.0,
            status="active",
        )
        db.add(owned)
        db.commit()
        db.refresh(owned)
        return owned

    @staticmethod
    def create_contact(db: Session, user_id: int, data: dict) -> UserContact:
        payload = data.copy()
        tags = payload.get("tags")
        payload["tags"] = json.dumps(tags) if tags else None
        contact = UserContact(user_id=user_id, **payload)
        db.add(contact)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def list_contacts(db: Session, user_id: int) -> list[UserContact]:
        return (
            db.query(UserContact)
            .filter(UserContact.user_id == user_id)
            .order_by(UserContact.created_at.desc())
            .all()
        )

    @staticmethod
    def update_contact(db: Session, user_id: int, contact_id: int, data: dict) -> UserContact:
        contact = (
            db.query(UserContact)
            .filter(UserContact.id == contact_id, UserContact.user_id == user_id)
            .first()
        )
        if not contact:
            raise NotFoundException(detail="Contact not found")

        for key, value in data.items():
            if key == "tags" and value is not None:
                setattr(contact, key, json.dumps(value))
            elif value is not None:
                setattr(contact, key, value)

        contact.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(contact)
        return contact

    @staticmethod
    def delete_contact(db: Session, user_id: int, contact_id: int) -> None:
        contact = (
            db.query(UserContact)
            .filter(UserContact.id == contact_id, UserContact.user_id == user_id)
            .first()
        )
        if not contact:
            raise NotFoundException(detail="Contact not found")
        db.delete(contact)
        db.commit()
