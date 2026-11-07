"""Specialty endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SpecialtyCreate, SpecialtyRead, SpecialtyUpdate
from app.security import CurrentAdminId
from app.services import specialties as service

router = APIRouter(prefix="/specialties", tags=["specialties"])


@router.get("", response_model=list[SpecialtyRead])
def list_specialties(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> list[SpecialtyRead]:
    return service.list_specialties(db)


@router.post("", response_model=SpecialtyRead, status_code=201)
def create_specialty(
    payload: SpecialtyCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> SpecialtyRead:
    return service.create_specialty(db, payload)


@router.put("/{specialty_id}", response_model=SpecialtyRead)
def update_specialty(
    specialty_id: int,
    payload: SpecialtyUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> SpecialtyRead:
    return service.update_specialty(db, specialty_id, payload)