"""Doctor endpoints."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor
from app.schemas import DoctorCreate, DoctorRead, DoctorUpdate, TimeSlotRead
from app.security import CurrentAdminId
from app.services import doctors as service
from app.services import slots as slots_service

router = APIRouter(prefix="/doctors", tags=["doctors"])


def _to_read(doctor: Doctor) -> DoctorRead:
    return DoctorRead(
        id=doctor.id,
        first_name=doctor.first_name,
        last_name=doctor.last_name,
        license_number=doctor.license_number,
        phone=doctor.phone,
        email=doctor.email,
        specialty_id=doctor.specialty_id,
        specialty_name=doctor.specialty.name,
        is_active=doctor.is_active,
    )


@router.get("", response_model=list[DoctorRead])
def list_doctors(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
    specialty_id: int | None = None,
    is_active: bool | None = None,
) -> list[DoctorRead]:
    doctors = service.list_doctors(db, specialty_id=specialty_id, is_active=is_active)
    return [_to_read(d) for d in doctors]


@router.post("", response_model=DoctorRead, status_code=201)
def create_doctor(
    payload: DoctorCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> DoctorRead:
    return _to_read(service.create_doctor(db, payload))


@router.put("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: int,
    payload: DoctorUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> DoctorRead:
    return _to_read(service.update_doctor(db, doctor_id, payload))


@router.get("/{doctor_id}/availability", response_model=list[TimeSlotRead])
def get_availability(
    doctor_id: int,
    date: date,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> list[TimeSlotRead]:
    return slots_service.get_availability(db, doctor_id, date)