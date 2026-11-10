"""Appointment endpoints."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Appointment, AppointmentStatus
from app.schemas import AppointmentCreate, AppointmentRead, AppointmentUpdate
from app.security import CurrentAdminId
from app.services import appointments as service

router = APIRouter(prefix="/appointments", tags=["appointments"])


def _to_read(a: Appointment) -> AppointmentRead:
    return AppointmentRead(
        id=a.id,
        patient_id=a.patient_id,
        patient_first_name=a.patient.first_name,
        patient_last_name=a.patient.last_name,
        doctor_id=a.doctor_id,
        doctor_first_name=a.doctor.first_name,
        doctor_last_name=a.doctor.last_name,
        specialty_id=a.doctor.specialty_id,
        specialty_name=a.doctor.specialty.name,
        date=a.date,
        start_time=a.start_time,
        end_time=a.end_time,
        reason=a.reason,
        status=a.status,
        notes=a.notes,
        created_at=a.created_at,
    )


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
    doctor_id: int | None = None,
    specialty_id: int | None = None,
    patient_id: int | None = None,
    target_date: date | None = Query(default=None, alias="date"),
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
) -> list[AppointmentRead]:
    appointments = service.list_appointments(
        db,
        doctor_id=doctor_id,
        specialty_id=specialty_id,
        patient_id=patient_id,
        target_date=target_date,
        status_filter=status_filter,
    )
    return [_to_read(a) for a in appointments]


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentRead:
    return _to_read(service.create_appointment(db, payload))


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentRead:
    return _to_read(service.update_appointment(db, appointment_id, payload))