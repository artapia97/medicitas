"""Public schedule service (read-only, internal network only)."""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import TIMEZONE
from app.models import Appointment, AppointmentStatus, Doctor
from app.schemas import PublicScheduleItemRead


def today_in_business_tz() -> date:
    return datetime.now(ZoneInfo(TIMEZONE)).date()


def list_public_schedule(
    db: Session,
    doctor_id: int | None = None,
    target_date: date | None = None,
) -> list[Appointment]:
    effective_date = target_date if target_date is not None else today_in_business_tz()
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.specialty),
        )
        .where(
            Appointment.date == effective_date,
            Appointment.status == AppointmentStatus.SCHEDULED.value,
        )
        .order_by(Appointment.start_time)
    )
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    return list(db.scalars(stmt))


def to_public_item(appointment: Appointment) -> PublicScheduleItemRead:
    return PublicScheduleItemRead(
        date=appointment.date,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        doctor_first_name=appointment.doctor.first_name,
        doctor_last_name=appointment.doctor.last_name,
        specialty_name=appointment.doctor.specialty.name,
        patient_first_name=appointment.patient.first_name,
        patient_last_name=appointment.patient.last_name,
    )