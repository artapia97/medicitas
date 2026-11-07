"""Password hashing and JWT handling for the administrator."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

ALGORITHM = "HS256"

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(admin_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_admin_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Token de autenticación ausente.")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("La sesión ha expirado. Inicie sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.")
    sub = payload.get("sub")
    try:
        return int(sub)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido.")


CurrentAdminId = Annotated[int, Depends(get_current_admin_id)]