"""Slot calculation and availability service."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import (
    AFTERNOON_LAST_SLOT,
    AFTERNOON_START,
    BUSINESS_DAYS,
    MORNING_LAST_SLOT,
    MORNING_START,
    SLOT_DURATION_MINUTES,
    TIMEZONE,
)
from app.models import Appointment, AppointmentStatus, Doctor
from app.schemas import TimeSlotRead


def add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(date.today(), t) + timedelta(minutes=minutes)).time()


def business_slots() -> list[time]:
    slots: list[time] = []
    t = MORNING_START
    while t <= MORNING_LAST_SLOT:
        slots.append(t)
        t = add_minutes(t, SLOT_DURATION_MINUTES)
    t = AFTERNOON_START
    while t <= AFTERNOON_LAST_SLOT:
        slots.append(t)
        t = add_minutes(t, SLOT_DURATION_MINUTES)
    return slots


def get_availability(
    db: Session, doctor_id: int, target_date: date
) -> list[TimeSlotRead]:
    doctor = db.get(Doctor, doctor_id)
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

    if target_date.weekday() not in BUSINESS_DAYS:
        return []

    appointments = list(
        db.scalars(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.date == target_date,
                Appointment.status != AppointmentStatus.CANCELLED.value,
            )
        )
    )
    by_start = {a.start_time: a for a in appointments}

    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    current_time = now.time()

    result: list[TimeSlotRead] = []
    for start in business_slots():
        end = add_minutes(start, SLOT_DURATION_MINUTES)
        appointment = by_start.get(start)
        if target_date < today:
            available = False
        elif target_date == today and start <= current_time:
            available = False
        else:
            available = appointment is None
        result.append(
            TimeSlotRead(
                start_time=start,
                end_time=end,
                available=available,
                appointment_id=appointment.id if appointment is not None else None,
                status=appointment.status if appointment is not None else None,
            )
        )
    return result