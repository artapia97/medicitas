"""Patient endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PatientCreate, PatientRead, PatientUpdate
from app.security import CurrentAdminId
from app.services import patients as service

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientRead])
def list_patients(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
    search: str | None = None,
    is_active: bool | None = None,
) -> list[PatientRead]:
    return service.list_patients(db, search=search, is_active=is_active)


@router.post("", response_model=PatientRead, status_code=201)
def create_patient(
    payload: PatientCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> PatientRead:
    return service.create_patient(db, payload)


@router.put("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> PatientRead:
    return service.update_patient(db, patient_id, payload)