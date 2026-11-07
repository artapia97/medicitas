"""Doctor management service."""
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import TIMEZONE
from app.models import Appointment, AppointmentStatus, Doctor, Specialty
from app.schemas import DoctorCreate, DoctorUpdate


def list_doctors(
    db: Session,
    specialty_id: int | None = None,
    is_active: bool | None = None,
) -> list[Doctor]:
    stmt = (
        select(Doctor)
        .options(joinedload(Doctor.specialty))
        .order_by(Doctor.last_name, Doctor.first_name)
    )
    if specialty_id is not None:
        stmt = stmt.where(Doctor.specialty_id == specialty_id)
    if is_active is not None:
        stmt = stmt.where(Doctor.is_active == is_active)
    return list(db.scalars(stmt))


def _get(db: Session, doctor_id: int) -> Doctor:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Médico no encontrado.",
        )
    return doctor


def _ensure_specialty(db: Session, specialty_id: int) -> None:
    if db.get(Specialty, specialty_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Especialidad no encontrada.",
        )


def _ensure_unique_license(
    db: Session, license_number: str, exclude_id: int | None = None
) -> None:
    stmt = select(Doctor).where(Doctor.license_number == license_number)
    if exclude_id is not None:
        stmt = stmt.where(Doctor.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un médico con ese número de registro.",
        )


def _future_scheduled_count(db: Session, doctor_id: int) -> int:
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    current_time = now.time()
    stmt = select(func.count(Appointment.id)).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatus.SCHEDULED.value,
        or_(
            Appointment.date > today,
            and_(Appointment.date == today, Appointment.start_time > current_time),
        ),
    )
    return db.scalar(stmt) or 0


def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    _ensure_specialty(db, payload.specialty_id)
    _ensure_unique_license(db, payload.license_number)
    doctor = Doctor(
        first_name=payload.first_name,
        last_name=payload.last_name,
        license_number=payload.license_number,
        phone=payload.phone,
        email=payload.email,
        specialty_id=payload.specialty_id,
        is_active=True,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def update_doctor(db: Session, doctor_id: int, payload: DoctorUpdate) -> Doctor:
    doctor = _get(db, doctor_id)
    _ensure_specialty(db, payload.specialty_id)
    _ensure_unique_license(db, payload.license_number, exclude_id=doctor.id)

    if doctor.is_active and not payload.is_active:
        count = _future_scheduled_count(db, doctor.id)
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El médico tiene {count} cita(s) futura(s) agendada(s). "
                    "Debe cancelarlas antes de desactivarlo."
                ),
            )

    doctor.first_name = payload.first_name
    doctor.last_name = payload.last_name
    doctor.license_number = payload.license_number
    doctor.phone = payload.phone
    doctor.email = payload.email
    doctor.specialty_id = payload.specialty_id
    doctor.is_active = payload.is_active
    db.commit()
    db.refresh(doctor)
    return doctor