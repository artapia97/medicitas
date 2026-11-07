"""SQLAlchemy models for MediCitas."""
import enum
import unicodedata
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import TIMEZONE
from app.database import Base


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"
    ATTENDED = "ATTENDED"
    NO_SHOW = "NO_SHOW"


def normalize_name(name: str) -> str:
    """Return name lowercased, without accents and with surrounding whitespace stripped."""
    decomposed = unicodedata.normalize("NFKD", name.strip())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _now_local() -> datetime:
    """Current time in the configured business timezone, stored naive for SQLite."""
    return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150))


class Specialty(Base):
    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    normalized_name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))

    doctors: Mapped[list["Doctor"]] = relationship(back_populates="specialty")


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    license_number: Mapped[str] = mapped_column(String(50), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"))
    is_active: Mapped[bool] = mapped_column(default=True)

    specialty: Mapped["Specialty"] = relationship(back_populates="doctors")
    appointments: Mapped[list["Appointment"]] = relationship(back_populates="doctor")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    national_id: Mapped[str] = mapped_column(String(20), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    birth_date: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(default=True)

    appointments: Mapped[list["Appointment"]] = relationship(back_populates="patient")


class Appointment(Base):
    __tablename__ = "appointments"

    __table_args__ = (
        Index(
            "uq_appointments_doctor_slot",
            "doctor_id", "date", "start_time",
            unique=True,
            sqlite_where=text("status != 'CANCELLED'"),
        ),
        Index(
            "uq_appointments_patient_slot",
            "patient_id", "date", "start_time",
            unique=True,
            sqlite_where=text("status != 'CANCELLED'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        String(20), default=AppointmentStatus.SCHEDULED.value
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now_local
    )

    patient: Mapped["Patient"] = relationship(back_populates="appointments")
    doctor: Mapped["Doctor"] = relationship(back_populates="appointments")

    def cancel(self) -> None:
        self._require_scheduled("cancelar")
        self.status = AppointmentStatus.CANCELLED.value

    def mark_attended(self) -> None:
        self._require_scheduled("marcar como ATTENDED")
        self.status = AppointmentStatus.ATTENDED.value

    def mark_no_show(self) -> None:
        self._require_scheduled("marcar como NO_SHOW")
        self.status = AppointmentStatus.NO_SHOW.value

    def _require_scheduled(self, action: str) -> None:
        if self.status != AppointmentStatus.SCHEDULED.value:
            raise ValueError(
                f"No se puede {action} una cita en estado {self.status}."
            )