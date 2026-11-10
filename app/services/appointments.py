"""Appointment management service."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import BUSINESS_DAYS, SLOT_DURATION_MINUTES, TIMEZONE
from app.models import Appointment, AppointmentStatus, Doctor, Patient
from app.schemas import AppointmentCreate, AppointmentUpdate
from app.services.slots import add_minutes, business_slots


def _now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))


def _has_started(target_date: date, start_time: time, now: datetime) -> bool:
    if target_date < now.date():
        return True
    if target_date > now.date():
        return False
    return start_time <= now.time()


def _validate_slot(target_date: date, start_time: time) -> None:
    if target_date.weekday() not in BUSINESS_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El centro no atiende ese día.",
        )
    if start_time not in business_slots():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El turno seleccionado no es válido.",
        )


def _check_doctor_conflict(
    db: Session, doctor_id: int, target_date: date, start_time: time
) -> None:
    exists = db.scalar(
        select(Appointment.id).where(
            Appointment.doctor_id == doctor_id,
            Appointment.date == target_date,
            Appointment.start_time == start_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El médico ya tiene una cita en ese turno.",
        )


def _check_patient_conflict(
    db: Session, patient_id: int, target_date: date, start_time: time
) -> None:
    exists = db.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient_id,
            Appointment.date == target_date,
            Appointment.start_time == start_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente ya tiene una cita en ese turno.",
        )


def list_appointments(
    db: Session,
    doctor_id: int | None = None,
    specialty_id: int | None = None,
    patient_id: int | None = None,
    target_date: date | None = None,
    status_filter: AppointmentStatus | None = None,
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.specialty),
        )
        .order_by(Appointment.date, Appointment.start_time)
    )
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if specialty_id is not None:
        stmt = stmt.where(Appointment.doctor.has(Doctor.specialty_id == specialty_id))
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if target_date is not None:
        stmt = stmt.where(Appointment.date == target_date)
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter.value)
    return list(db.scalars(stmt))


def create_appointment(db: Session, payload: AppointmentCreate) -> Appointment:
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado.",
        )
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente está desactivado.",
        )

    doctor = db.get(Doctor, payload.doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Médico no encontrado.",
        )
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El médico está desactivado.",
        )

    _validate_slot(payload.date, payload.start_time)

    if _has_started(payload.date, payload.start_time, _now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede agendar una cita en una fecha u hora pasada.",
        )

    _check_doctor_conflict(db, payload.doctor_id, payload.date, payload.start_time)
    _check_patient_conflict(db, payload.patient_id, payload.date, payload.start_time)

    appointment = Appointment(
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=add_minutes(payload.start_time, SLOT_DURATION_MINUTES),
        reason=payload.reason,
        status=AppointmentStatus.SCHEDULED.value,
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El turno seleccionado ya está ocupado.",
        )
    db.refresh(appointment)
    return appointment


def _apply_transition(action) -> None:
    try:
        action()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def update_appointment(
    db: Session, appointment_id: int, payload: AppointmentUpdate
) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada.",
        )

    if payload.status is not None:
        new_status = payload.status.value
        if new_status != appointment.status:
            if new_status in (
                AppointmentStatus.ATTENDED.value,
                AppointmentStatus.NO_SHOW.value,
            ) and not _has_started(appointment.date, appointment.start_time, _now()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Solo se puede marcar ATTENDED o NO_SHOW cuando "
                        "ya llegó la hora de inicio de la cita."
                    ),
                )
            if new_status == AppointmentStatus.CANCELLED.value:
                _apply_transition(appointment.cancel)
            elif new_status == AppointmentStatus.ATTENDED.value:
                _apply_transition(appointment.mark_attended)
            else:
                _apply_transition(appointment.mark_no_show)

    if "notes" in payload.model_fields_set:
        appointment.notes = payload.notes

    db.commit()
    db.refresh(appointment)
    return appointment