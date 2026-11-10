"""Public schedule endpoint (no auth, restricted to internal network)."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PublicScheduleItemRead
from app.security import require_internal_network
from app.services import public_schedule as service

router = APIRouter(
    prefix="/public-schedule",
    tags=["public-schedule"],
    dependencies=[Depends(require_internal_network)],
)


@router.get("", response_model=list[PublicScheduleItemRead])
def get_public_schedule(
    db: Annotated[Session, Depends(get_db)],
    doctor_id: int | None = None,
    target_date: date | None = Query(default=None, alias="date"),
) -> list[PublicScheduleItemRead]:
    appointments = service.list_public_schedule(
        db, doctor_id=doctor_id, target_date=target_date
    )
    return [service.to_public_item(a) for a in appointments]