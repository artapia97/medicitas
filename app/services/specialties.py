"""Specialty management service."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Specialty, normalize_name
from app.schemas import SpecialtyCreate, SpecialtyUpdate


def list_specialties(db: Session) -> list[Specialty]:
    return list(db.scalars(select(Specialty).order_by(Specialty.name)))


def _ensure_unique_name(db: Session, name: str, exclude_id: int | None = None) -> None:
    normalized = normalize_name(name)
    stmt = select(Specialty).where(Specialty.normalized_name == normalized)
    if exclude_id is not None:
        stmt = stmt.where(Specialty.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una especialidad con ese nombre.",
        )


def _get(db: Session, specialty_id: int) -> Specialty:
    specialty = db.get(Specialty, specialty_id)
    if specialty is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Especialidad no encontrada.",
        )
    return specialty


def create_specialty(db: Session, payload: SpecialtyCreate) -> Specialty:
    _ensure_unique_name(db, payload.name)
    specialty = Specialty(
        name=payload.name,
        normalized_name=normalize_name(payload.name),
        description=payload.description,
    )
    db.add(specialty)
    db.commit()
    db.refresh(specialty)
    return specialty


def update_specialty(db: Session, specialty_id: int, payload: SpecialtyUpdate) -> Specialty:
    specialty = _get(db, specialty_id)
    _ensure_unique_name(db, payload.name, exclude_id=specialty.id)
    specialty.name = payload.name
    specialty.normalized_name = normalize_name(payload.name)
    specialty.description = payload.description
    db.commit()
    db.refresh(specialty)
    return specialty