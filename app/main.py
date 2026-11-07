"""FastAPI entry point for MediCitas."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT
from app.database import Base, engine
from app import models  # noqa: F401  (register models with Base.metadata)
from app.seed import seed_database

STATIC_DIR = PROJECT_ROOT / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


app = FastAPI(title="MediCitas", lifespan=lifespan)

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")