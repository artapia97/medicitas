"""Patient management service."""
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.config import TIMEZONE
from app.models import Appointment, AppointmentStatus, Patient, normalize_name
from app.schemas import PatientCreate, PatientUpdate


def list_patients(
    db: Session,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Patient]:
    stmt = select(Patient).order_by(Patient.last_name, Patient.first_name)
    if is_active is not None:
        stmt = stmt.where(Patient.is_active == is_active)
    patients = list(db.scalars(stmt))
    if search and search.strip():
        query = search.strip()
        normalized_query = normalize_name(query)
        patients = [
            p for p in patients
            if query in p.national_id
            or normalized_query in normalize_name(p.first_name)
            or normalized_query in normalize_name(p.last_name)
        ]
    return patients


def _get(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado.",
        )
    return patient


def _ensure_unique_national_id(
    db: Session, national_id: str, exclude_id: int | None = None
) -> None:
    stmt = select(Patient).where(Patient.national_id == national_id)
    if exclude_id is not None:
        stmt = stmt.where(Patient.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un paciente con esa cédula.",
        )


def _future_scheduled_count(db: Session, patient_id: int) -> int:
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    current_time = now.time()
    stmt = select(func.count(Appointment.id)).where(
        Appointment.patient_id == patient_id,
        Appointment.status == AppointmentStatus.SCHEDULED.value,
        or_(
            Appointment.date > today,
            and_(Appointment.date == today, Appointment.start_time > current_time),
        ),
    )
    return db.scalar(stmt) or 0


def create_patient(db: Session, payload: PatientCreate) -> Patient:
    _ensure_unique_national_id(db, payload.national_id)
    patient = Patient(
        national_id=payload.national_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        birth_date=payload.birth_date,
        phone=payload.phone,
        email=payload.email,
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient_id: int, payload: PatientUpdate) -> Patient:
    patient = _get(db, patient_id)
    _ensure_unique_national_id(db, payload.national_id, exclude_id=patient.id)

    if patient.is_active and not payload.is_active:
        count = _future_scheduled_count(db, patient.id)
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El paciente tiene {count} cita(s) futura(s) agendada(s). "
                    "Debe cancelarlas antes de desactivarlo."
                ),
            )

    patient.national_id = payload.national_id
    patient.first_name = payload.first_name
    patient.last_name = payload.last_name
    patient.birth_date = payload.birth_date
    patient.phone = payload.phone
    patient.email = payload.email
    patient.is_active = payload.is_active
    db.commit()
    db.refresh(patient)
    return patient