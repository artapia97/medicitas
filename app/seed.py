"""Database seeding: admin bootstrap and sample data."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

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
    settings,
)
from app.database import SessionLocal
from app.models import (
    Admin,
    Appointment,
    AppointmentStatus,
    Doctor,
    Patient,
    Specialty,
    normalize_name,
)
from app.security import hash_password


def _add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(date.today(), t) + timedelta(minutes=minutes)).time()


def _business_slots() -> list[time]:
    slots: list[time] = []
    t = MORNING_START
    while t <= MORNING_LAST_SLOT:
        slots.append(t)
        t = _add_minutes(t, SLOT_DURATION_MINUTES)
    t = AFTERNOON_START
    while t <= AFTERNOON_LAST_SLOT:
        slots.append(t)
        t = _add_minutes(t, SLOT_DURATION_MINUTES)
    return slots


def _next_business_day(d: date) -> date:
    d = d + timedelta(days=1)
    while d.weekday() not in BUSINESS_DAYS:
        d = d + timedelta(days=1)
    return d


def _create_admin_if_missing(db: Session) -> None:
    if db.scalar(select(Admin).limit(1)) is not None:
        return
    db.add(
        Admin(
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            full_name=settings.admin_full_name,
        )
    )


def _has_business_data(db: Session) -> bool:
    return any(
        db.scalar(select(model).limit(1)) is not None
        for model in (Specialty, Doctor, Patient, Appointment)
    )


def _load_sample_data(db: Session) -> None:
    specialties = [
        Specialty(
            name="Medicina General",
            normalized_name=normalize_name("Medicina General"),
            description="Atención médica general",
        ),
        Specialty(
            name="Odontología",
            normalized_name=normalize_name("Odontología"),
            description="Salud dental",
        ),
        Specialty(
            name="Ginecología",
            normalized_name=normalize_name("Ginecología"),
            description="Salud femenina",
        ),
        Specialty(
            name="Psicología",
            normalized_name=normalize_name("Psicología"),
            description="Salud mental",
        ),
    ]
    db.add_all(specialties)
    db.flush()

    doctors = [
        Doctor(
            first_name="Ana", last_name="Pérez", license_number="MED-001",
            phone="0991111111", email="ana.perez@medicitas.local",
            specialty_id=specialties[0].id, is_active=True,
        ),
        Doctor(
            first_name="Luis", last_name="Gómez", license_number="MED-002",
            phone="0992222222", email="luis.gomez@medicitas.local",
            specialty_id=specialties[1].id, is_active=True,
        ),
        Doctor(
            first_name="María", last_name="Rodríguez", license_number="MED-003",
            phone="0993333333", email="maria.rodriguez@medicitas.local",
            specialty_id=specialties[2].id, is_active=True,
        ),
        Doctor(
            first_name="Carlos", last_name="Vera", license_number="MED-004",
            phone="0994444444", email="carlos.vera@medicitas.local",
            specialty_id=specialties[3].id, is_active=True,
        ),
    ]
    db.add_all(doctors)

    patients = [
        Patient(
            national_id="0102030405", first_name="Juan", last_name="López",
            birth_date=date(1990, 5, 12), phone="0980000001",
            email="juan.lopez@example.com", is_active=True,
        ),
        Patient(
            national_id="0102030406", first_name="Ana", last_name="Torres",
            birth_date=date(1985, 3, 20), phone="0980000002",
            email="ana.torres@example.com", is_active=True,
        ),
        Patient(
            national_id="0102030407", first_name="Pedro", last_name="Ramírez",
            birth_date=date(1978, 11, 2), phone="0980000003",
            email="pedro.ramirez@example.com", is_active=True,
        ),
        Patient(
            national_id="0102030408", first_name="Lucía", last_name="Mendoza",
            birth_date=date(2000, 7, 15), phone="0980000004",
            email="lucia.mendoza@example.com", is_active=True,
        ),
        Patient(
            national_id="0102030409", first_name="Diego", last_name="Castro",
            birth_date=date(1995, 1, 8), phone="0980000005",
            email="diego.castro@example.com", is_active=True,
        ),
    ]
    db.add_all(patients)
    db.flush()

    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    current_time = now.time()

    slots = _business_slots()
    past_slots: list[time] = []
    future_slots: list[time] = []
    if today.weekday() in BUSINESS_DAYS:
        past_slots = [s for s in slots if s <= current_time]
        future_slots = [s for s in slots if s > current_time]

    appointments: list[Appointment] = []

    def _make(
        patient_idx: int, doctor_idx: int, d: date, start: time, reason: str
    ) -> None:
        appointments.append(
            Appointment(
                patient_id=patients[patient_idx].id,
                doctor_id=doctors[doctor_idx].id,
                date=d,
                start_time=start,
                end_time=_add_minutes(start, SLOT_DURATION_MINUTES),
                reason=reason,
                status=AppointmentStatus.SCHEDULED.value,
            )
        )

    # Hoy: 2 turnos ya transcurridos y hasta 2 futuros (si el día lo permite).
    if len(past_slots) >= 2:
        _make(0, 0, today, past_slots[-2], "Control general")
        _make(1, 1, today, past_slots[-1], "Limpieza dental")
    elif len(past_slots) == 1:
        _make(0, 0, today, past_slots[0], "Control general")
    if future_slots:
        _make(2, 2, today, future_slots[0], "Consulta ginecológica")
    if len(future_slots) >= 2:
        _make(3, 3, today, future_slots[1], "Consulta de seguimiento")

    # Siguiente día hábil.
    next_day = _next_business_day(today)
    _make(4, 0, next_day, slots[0], "Chequeo general")
    _make(3, 3, next_day, slots[4], "Primera consulta psicológica")

    # Otro día hábil.
    day_after = _next_business_day(next_day)
    _make(0, 1, day_after, slots[6], "Revisión dental")
    _make(1, 2, day_after, slots[10], "Control ginecológico")

    db.add_all(appointments)


def seed_database() -> None:
    """Create the admin if missing and load sample data when enabled and empty."""
    with SessionLocal() as db:
        _create_admin_if_missing(db)
        if settings.load_sample_data and not _has_business_data(db):
            _load_sample_data(db)
        db.commit()