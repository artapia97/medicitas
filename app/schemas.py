"""Pydantic schemas for request/response models."""
import re
from datetime import date, datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import AppointmentStatus

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None


class SpecialtyCreate(SpecialtyBase):
    pass


class SpecialtyUpdate(SpecialtyBase):
    pass


class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None


class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    specialty_id: int

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(DoctorBase):
    is_active: bool


class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    license_number: str
    phone: str | None
    email: str | None
    specialty_id: int
    specialty_name: str
    is_active: bool


class PatientBase(BaseModel):
    national_id: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    phone: str = Field(min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=150)

    @field_validator("national_id", "first_name", "last_name", "phone")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

    @field_validator("birth_date")
    @classmethod
    def _no_future_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return v


class PatientCreate(PatientBase):
    pass


class PatientUpdate(PatientBase):
    is_active: bool


class PatientRead(BaseModel):
    id: int
    national_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    phone: str
    email: str | None
    is_active: bool


class TimeSlotRead(BaseModel):
    start_time: time
    end_time: time
    available: bool
    appointment_id: int | None = None
    status: str | None = None


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    start_time: time
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El motivo es obligatorio.")
        return v


class AppointmentUpdate(BaseModel):
    status: AppointmentStatus | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _require_any_field(self) -> "AppointmentUpdate":
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        return self


class AppointmentRead(BaseModel):
    id: int
    patient_id: int
    patient_first_name: str
    patient_last_name: str
    doctor_id: int
    doctor_first_name: str
    doctor_last_name: str
    specialty_id: int
    specialty_name: str
    date: date
    start_time: time
    end_time: time
    reason: str
    status: str
    notes: str | None
    created_at: datetime


class PublicScheduleItemRead(BaseModel):
    date: date
    start_time: time
    end_time: time
    doctor_first_name: str
    doctor_last_name: str
    specialty_name: str
    patient_first_name: str
    patient_last_name: str