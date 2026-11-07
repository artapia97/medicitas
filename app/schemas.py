"""Pydantic schemas for request/response models."""
from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int