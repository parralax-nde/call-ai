import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from shared.auth import get_password_hash, verify_password
from shared.exceptions import BadRequestException, ConflictException, NotFoundException

from .models import BlacklistedToken, User


class AuthService:
    @staticmethod
    def register_user(db: Session, email: str, password: str) -> User:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise ConflictException(detail="Email already registered")

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def blacklist_token(db: Session, token: str) -> None:
        blacklisted = BlacklistedToken(token=token)
        db.add(blacklisted)
        db.commit()

    @staticmethod
    def is_token_blacklisted(db: Session, token: str) -> bool:
        entry = (
            db.query(BlacklistedToken)
            .filter(BlacklistedToken.token == token)
            .first()
        )
        return entry is not None

    @staticmethod
    def get_or_create_google_user(db: Session, google_id: str, email: str) -> User:
        user = db.query(User).filter(User.google_id == google_id).first()
        if user:
            return user

        # Check if a user with this email already exists
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id
            db.commit()
            db.refresh(user)
            return user

        user = User(
            email=email,
            google_id=google_id,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def create_password_reset_token(db: Session, email: str) -> str:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise NotFoundException(detail="User not found")
        return secrets.token_urlsafe(32)

    @staticmethod
    def reset_password(db: Session, token: str, new_password: str) -> None:
        if not token:
            raise BadRequestException(detail="Invalid or expired reset token")

        # In a real implementation, the token would be validated against
        # a stored reset token. For now, we treat any non-empty token
        # as valid and reset the first matching user placeholder.
        raise BadRequestException(detail="Invalid or expired reset token")
