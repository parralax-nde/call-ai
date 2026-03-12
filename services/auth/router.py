from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from shared.auth import create_access_token, get_current_user, oauth2_scheme
from shared.database import get_db
from shared.exceptions import BadRequestException, UnauthorizedException

from .schemas import (
    GoogleAuthRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenResponse,
    UserRegister,
    UserLogin,
    UserResponse,
)
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserRegister, db: Session = Depends(get_db)) -> UserResponse:
    user = auth_service.register_user(db, user_data.email, user_data.password)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise UnauthorizedException(detail="Invalid email or password")
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token)


@router.post("/logout")
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    auth_service.blacklist_token(db, token)
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    token: str = Depends(oauth2_scheme),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if auth_service.is_token_blacklisted(db, token):
        raise UnauthorizedException(detail="Token has been blacklisted")
    new_token = create_access_token(
        data={"sub": current_user["sub"], "email": current_user.get("email", "")}
    )
    return TokenResponse(access_token=new_token)


@router.post("/google", response_model=TokenResponse)
def google_auth(
    auth_data: GoogleAuthRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    # Mock Google token verification: extract a google_id from the token
    google_id = auth_data.token
    if not google_id:
        raise BadRequestException(detail="Invalid Google token")
    email = f"{google_id}@gmail.com"
    user = auth_service.get_or_create_google_user(db, google_id, email)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "is_admin": user.is_admin}
    )
    return TokenResponse(access_token=access_token)


@router.post("/password-reset")
def request_password_reset(
    reset_data: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict:
    auth_service.create_password_reset_token(db, reset_data.email)
    return {"message": "Password reset instructions have been sent to your email"}


@router.post("/password-reset/confirm")
def confirm_password_reset(
    reset_data: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict:
    auth_service.reset_password(db, reset_data.token, reset_data.new_password)
    return {"message": "Password has been reset successfully"}
