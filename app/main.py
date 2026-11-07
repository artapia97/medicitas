"""FastAPI entry point for MediCitas."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (register models with Base.metadata)
from app.config import PROJECT_ROOT
from app.database import Base, engine
from app.routers import auth as auth_router
from app.routers import doctors as doctors_router
from app.routers import specialties as specialties_router
from app.seed import seed_database

STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(title="MediCitas", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    detail = "Datos de entrada inválidos."
    if errors:
        loc = errors[0].get("loc") or ()
        field = loc[-1] if loc else None
        if isinstance(field, str) and field not in {"body", "query", "path"}:
            detail = f"El campo '{field}' no es válido."
    return JSONResponse(status_code=422, content={"detail": detail})


app.include_router(auth_router.router, prefix="/api")
app.include_router(specialties_router.router, prefix="/api")
app.include_router(doctors_router.router, prefix="/api")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")