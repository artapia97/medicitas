"""Authentication service for the administrator."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Admin
from app.schemas import LoginRequest, LoginResponse
from app.security import create_access_token, verify_password


def authenticate(db: Session, username: str, password: str) -> Admin:
    admin = db.scalar(select(Admin).where(Admin.username == username))
    if admin is None or not verify_password(password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin


def login(db: Session, payload: LoginRequest) -> LoginResponse:
    admin = authenticate(db, payload.username, payload.password)
    token = create_access_token(admin.id)
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )