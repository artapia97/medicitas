### Usuario

Actúa como un ingeniero de software senior con experiencia en Python, FastAPI y desarrollo web con HTML, CSS y JavaScript.

Vamos a construir juntos MediCitas siguiendo el diseno.md que te adjunto, que es la fuente de verdad del proyecto. La sección 12 tiene decisiones técnicas que ya tomé, respétalas. Es un proyecto académico: todo el código lo generas tú, pero trabajaremos paso a paso. Yo te pido un archivo a la vez, leo el código, y cuando tengamos algo que se pueda ejecutar lo pruebo.

Reglas:
- Genera solo lo que te pida, sin adelantar otras partes ni agregar funcionalidades fuera del diseño.
- Si algo contradice el diseño o no está claro, pregúntame antes de asumir.
- Sé breve. Entrega el archivo completo con su ruta y, como máximo, 3 o 4 puntos cortos con las decisiones importantes. No repitas el diseño ni hagas resúmenes largos.
- Código con nombres en inglés, respuestas en español.

Mi entorno es Windows 11, Python 3.14 y PowerShell.

Para empezar, dime en pocas líneas si ves algo ambiguo o inconsistente en el diseño. No generes código todavía.

---

### DeepSeek AI

Revisé el diseño y veo cuatro puntos a aclarar antes de empezar:

- **Python 3.14**: al día de hoy no hay versión estable de 3.14 (la última es la serie 3.13). ¿Trabajo con 3.13 o quieres forzar 3.14? Afecta `pyproject`/`requirements` y algunas dependencias (SQLAlchemy, Pydantic).

- **Forma de las respuestas de listado**: el diseño no especifica si los `GET /api/doctors` y `GET /api/appointments` devuelven solo los IDs de las relaciones (`specialty_id`, `patient_id`, `doctor_id`) o también expanden los nombres (`specialty_name`, `patient_full_name`, `doctor_full_name`, `license_number`). RF-08/RF-10 los necesitan para mostrar; si no vienen expandidos hay que resolverlos en el frontend. ¿Los expando en el backend?

- **Agenda pública con `doctor_id` pero sin `date`**: RF-10 dice que por defecto muestra hoy, pero no aclara qué pasa si solo envían `doctor_id`. ¿`date` se vuelve obligatorio al filtrar por médico, o si falta se asume hoy?

- **Zona horaria en Windows**: para `America/Guayaquil` con `zoneinfo` (stdlib) hay que agregar `tzdata` a `requirements.txt`, porque Windows no trae la base IANA. ¿Lo incluyo, o prefieres fijar el offset `-05:00` como constante al ser Ecuador sin DST?

---

### Usuario

1. Python 3.14 sí es estable, salió en octubre de 2025 y tengo instalada la 3.14.7. Trabaja con 3.14 y versiones de dependencias compatibles.
2. Sí, expande los nombres en el backend.
3. Si no envían date, asume hoy.
4. Incluye tzdata.

Empecemos por requirements.txt y .env.example.

---

### DeepSeek AI

Listo. Versiones fijadas para Python 3.14; todas las dependencias declaran soporte explícito para 3.14 en sus metadatos o changelogs.

**`requirements.txt`**

```txt
fastapi==0.141.0
uvicorn[standard]==0.38.0
sqlalchemy==2.0.54
pydantic==2.13.0
pydantic-settings==2.12.0
bcrypt==5.0.0
PyJWT==2.12.0
tzdata==2025.2
```
**`.env.example`**

```env
# Obligatorias
SECRET_KEY=cambia-esto-por-una-clave-larga-y-aleatoria
ADMIN_PASSWORD=cambia-esto-por-una-contrasena-segura

# Administrador inicial
ADMIN_USERNAME=admin
ADMIN_FULL_NAME=Administrador MediCitas

# JWT
JWT_EXPIRATION_MINUTES=60

# Base de datos
DATABASE_FILENAME=medicitas.db

# Datos de prueba
LOAD_SAMPLE_DATA=true

# Redes internas permitidas para la agenda pública
INTERNAL_NETWORKS=127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16
```
**Decisiones:**

- `tzdata` fijado como dependencia directa porque `zoneinfo` en Windows no trae la base IANA.

- `uvicorn[standard]` incluye `uvloop`/`httptools`; en Windows `uvloop` no se instala, pero el extra es seguro.

- `INTERNAL_NETWORKS` se parsea como lista separada por comas en `Settings`; el valor por defecto del código coincide con el del `.env.example`.

- `LOAD_SAMPLE_DATA` se deja como `true` en el ejemplo para que al primer arranque haya datos; el código solo carga si las tablas de negocio están vacías.

---

### Usuario

Instalé las dependencias sin errores. Ahora genera app/config.py.

---

### DeepSeek AI

**`app/config.py`**

```python
"""Application configuration and business-rule constants."""
from datetime import time
from pathlib import Path
from typing import Final

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
ENV_FILE: Final[Path] = PROJECT_ROOT / ".env"

# Time zone used for "today", elapsed slots and JWT display.
TIMEZONE: Final[str] = "America/Guayaquil"

# Business days (Monday=0 ... Sunday=6). Sunday is not attended.
BUSINESS_DAYS: Final[tuple[int, ...]] = (0, 1, 2, 3, 4, 5)

# Daily schedule: morning 08:00-12:30 (10 slots), lunch break, afternoon 14:00-16:30 (6 slots).
MORNING_START: Final[time] = time(8, 0)
MORNING_LAST_SLOT: Final[time] = time(12, 30)
AFTERNOON_START: Final[time] = time(14, 0)
AFTERNOON_LAST_SLOT: Final[time] = time(16, 30)
SLOT_DURATION_MINUTES: Final[int] = 30

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str
    admin_username: str = "admin"
    admin_password: str
    admin_full_name: str = "Administrador MediCitas"
    jwt_expiration_minutes: int = 60
    database_filename: str = "medicitas.db"
    load_sample_data: bool = True
    internal_networks: str = "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    @property
    def database_path(self) -> Path:
        return PROJECT_ROOT / self.database_filename

    @property
    def internal_networks_list(self) -> list[str]:
        return [n.strip() for n in self.internal_networks.split(",") if n.strip()]

settings = Settings()
```
**Decisiones:**

- `SECRET_KEY` y `ADMIN_PASSWORD` sin default: si faltan en `.env`, `Settings()` falla al importar y la app no arranca (coherente con la sección 12).

- `INTERNAL_NETWORKS` se declara como `str` y se expone parseada en `internal_networks_list`; pydantic-settings intentaría JSON si fuera `list[str]`, y el `.env` usa comas.

- `database_path` resuelve siempre contra `PROJECT_ROOT`, no contra el directorio de ejecución. Si el `.env` trae una ruta absoluta, `pathlib` la respeta.

- Los horarios se modelan con `time`; el servicio de turnos solo itera entre `MORNING_START/MORNING_LAST_SLOT` y `AFTERNOON_START/AFTERNOON_LAST_SLOT` con `SLOT_DURATION_MINUTES`.

---

### Usuario

config.py funciona, cargó el .env sin problemas. Ahora genera el .gitignore y app/database.py.

---

### DeepSeek AI

**`.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
env/

# Entorno
.env

# Base de datos SQLite
*.db
*.db-journal

# Herramientas
.vscode/
.idea/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Sistema
Thumbs.db
.DS_Store
```
**`app/database.py`**

```python
"""SQLAlchemy engine, session factory and declarative base."""
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

DATABASE_URL = f"sqlite:///{settings.database_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)

class Base(DeclarativeBase):
    pass

@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```
**Decisiones:**

- `check_same_thread=False` porque FastAPI ejecuta los endpoints síncronos en un threadpool distinto al del arranque; sin esto SQLite falla al reutilizar la conexión.

- `PRAGMA foreign_keys = ON` a nivel de conexión: SQLite no aplica las FKs por defecto y el diseño las necesita (integridad referencial en `doctors`, `patients`, `appointments`).

- `expire_on_commit=False` para que los objetos sigan accesibles después del commit sin volver a consultar (útil al devolver respuestas Pydantic desde los routers).

- `Base` es el `DeclarativeBase` de SQLAlchemy 2; los modelos lo heredan y los índices únicos parciales se declaran en `__table_args__` de cada modelo.

---

### Usuario

Todo bien, la ruta de la base es correcta e hice el primer commit. Ahora genera app/models.py con los cinco modelos.

---

### DeepSeek AI

**`app/models.py`**

```python
"""SQLAlchemy models for MediCitas."""
import enum
import unicodedata
from datetime import UTC, date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
        DateTime, default=lambda: datetime.now(UTC)
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
```
**Decisiones:**

- `status` es `String(20)` con los valores del enum, tal como pide la sección 8; no se usa `Enum` nativo para que la base siga siendo legible con herramientas externas.

- Los índices únicos parciales usan `sqlite_where=text("status != 'CANCELLED'")`: garantizan a nivel de DB que un médico o paciente no tenga dos citas no canceladas en el mismo turno, y permiten reutilizar el turno tras cancelar.

- `normalize_name()` queda como helper público en este archivo; el servicio de especialidades lo llamará al crear y editar. No usé `@validates` para evitar que un recálculo silencioso al cargar desde la base contradiga lo almacenado.

- Los métodos `cancel/mark_attended/mark_no_show` solo validan la transición de estado (sección 12: "en un solo lugar"); la comprobación temporal (que la hora ya pasó) se hará en el servicio, que es quien conoce la zona horaria. Los tamaños de `String` son los que usarán los schemas de Pydantic.

---

### Usuario

Revisé models.py y está bien, pero created_at usa UTC y el diseño dice que las fechas se manejan en America/Guayaquil. Como SQLite no guarda la zona horaria, quedaría 5 horas adelantada. Corrígelo para que use la zona de config.py.

---

### DeepSeek AI

Tienes razón. Corrijo el import y el `default` de `created_at` para que use `TIMEZONE` de config. SQLite no guarda offset en `DateTime`, así que lo almaceno como naive ya convertido a Guayaquil (así lo que se lee de la base es la hora local del centro, sin sorpresas de conversión).

**Cambios en `app/models.py`** (reemplaza el bloque de imports y el `default` de `created_at`)

```python
"""SQLAlchemy models for MediCitas."""
import enum
import unicodedata
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import TIMEZONE
from app.database import Base

def _now_local() -> datetime:
    """Current time in the configured business timezone, stored naive for SQLite."""
    return datetime.now(ZoneInfo(TIMEZONE)).replace(tzinfo=None)
```
Y en `Appointment`:

```python
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_now_local
    )
```
**Decisiones:**

- `_now_local()` devuelve naive en hora de Guayaquil; como SQLite no conserva `tzinfo`, guardar aware haría que el valor se corrompa silenciosamente al reconstruirse. Al leer, lo que sale es directamente hora local del centro.

- `TIMEZONE` se importa de `config.py` (es la constante que la sección 12 describe como fija de negocio, no variable de entorno). JWT sigue en UTC porque así lo dice explícitamente la sección 12; son dos ámbitos distintos.

- No toqué `date`/`start_time`/`end_time` de las citas: ya vienen como `date`/`time` puros, sin zona.

---

### Usuario

La corrección está bien, pero pásame el models.py completo para reemplazarlo directamente. A partir de ahora entrégame siempre los archivos completos, no solo los cambios.

---

### DeepSeek AI

Entendido. De aquí en adelante, archivos completos.

**`app/models.py`**

```python
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
```
**Decisiones:**

- `created_at` se genera con `_now_local()` (hora de Guayaquil, naive), coherente con la zona de `config.py`.

- El resto del archivo queda igual que en la versión que ya validaste.

- Los métodos de transición siguen lanzando `ValueError`; el servicio lo traducirá a 400.

---

### Usuario

Ahora sí está completo. Genera app/security.py con el hash de contraseñas, la creación y validación del JWT y la dependencia para proteger los endpoints.



---

### DeepSeek AI

**`app/security.py`**

```python
"""Password hashing and JWT handling for the administrator."""
from datetime import UTC, datetime, timedelta
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

ALGORITHM = "HS256"

_bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

def create_access_token(admin_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_admin_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Token de autenticación ausente.")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("La sesión ha expirado. Inicie sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.")
    sub = payload.get("sub")
    try:
        return int(sub)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido.")

CurrentAdminId = Annotated[int, Depends(get_current_admin_id)]
```
**Decisiones:**

- `HTTPBearer(auto_error=False)` para controlar el 401 (FastAPI devolvería 403 con `auto_error=True`); se agrega `WWW-Authenticate: Bearer` como exige el estándar.

- `sub` se serializa como string porque PyJWT ≥2.10 rechaza `sub` numéricos al decodificar; se convierte a `int` al devolverlo.

- `iat`/`exp` en UTC (sección 12); el `exp` lo valida PyJWT automáticamente y se traduce a un mensaje claro en español.

- La dependencia no consulta la base: el único administrador existe siempre (sección 12) y el token solo se firma para él. `hash_password` deja que bcrypt lance si la contraseña excede 72 bytes; el límite se refuerza en el schema del login.

- La restricción por red interna para la agenda pública también pertenece a este módulo según la arquitectura; la dejo pendiente para que me la pidas cuando toque el endpoint público.

---

### Usuario

security.py está bien. Ahora genera app/seed.py.

---

### DeepSeek AI

**`app/seed.py`**

```python
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
    while t  date:
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
        past_slots = [s for s in slots if s  current_time]

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
```
**Decisiones:**

- `seed_database()` usa `SessionLocal` internamente y hace un solo `commit()`; el `main.py` solo la llamará en el arranque.

- Las citas del día actual se calculan a partir de `datetime.now(ZoneInfo(TIMEZONE))`: los slots cuyo inicio ya pasó van a `past_slots`, los futuros a `future_slots`. Si hoy es domingo o no hay slots transcurridos/futuros, simplemente no se crean esas citas.

- Los pares (paciente, médico) y turnos del seed están elegidos sin solaparse, para no violar los índices únicos parciales.

- El admin solo se crea si no existe; los datos de prueba solo si `LOAD_SAMPLE_DATA` es verdadero y no hay especialidades, médicos, pacientes ni citas. Reiniciar no duplica nada.

---

### Usuario

seed.py está bien. Ahora genera app/main.py. Por ahora sin endpoints: que arranque, cree las tablas, ejecute el seed y sirva la carpeta static, para probar que todo funciona hasta aquí.

---

### DeepSeek AI

**`app/__init__.py`**

```python

```
**`app/main.py`**

```python
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
```
**`static/index.html`** (placeholder para verificar el montaje)

```html

    MediCitas

    MediCitas
    Servidor en marcha. La agenda pública se implementará más adelante.

```
**Decisiones:**

- `lifespan` en vez de `@app.on_event` (deprecado en FastAPI moderno); las tablas se crean y el seed se ejecuta antes de aceptar peticiones.

- `import models` con `# noqa` para que `Base.metadata` conozca las cinco tablas antes de `create_all`; sin él las tablas no se crearían.

- `StaticFiles(html=True)` en la raíz sirve `index.html` en `/`. Los routers `/api/*` se montarán después y tendrán prioridad sobre el catch-all de `static` (Starlette resuelve rutas antes que mounts).

- `STATIC_DIR` se resuelve contra `PROJECT_ROOT`, igual que la base de datos; si la carpeta no existiera, `StaticFiles` falla al importar, por eso entrego ya el `index.html` placeholder.

Prueba: `uvicorn app.main:app --reload` y abre http://127.0.0.1:8000/ y http://127.0.0.1:8000/docs. La base `medicitas.db` debe aparecer con las 5 tablas y el seed cargado.

---

### Usuario

Punto de control superado: la app arranca, sirve la página, Swagger funciona y la base se creó con el admin y los datos de prueba, con la hora local correcta en created_at.
Antes de seguir, dime en una lista corta qué archivos faltan para completar el backend y qué contiene cada uno. Todavía sin código.

---

### DeepSeek AI

Faltan estos archivos (backend):

- **`app/security.py`** (ampliación) — restricción por red interna: función que valida la IP de la conexión contra `INTERNAL_NETWORKS` y una dependencia FastAPI que responde 403 si no cumple.

- **`app/schemas.py`** — modelos Pydantic v2 de entrada/salida para auth, especialidades, médicos, pacientes, citas, disponibilidad (`TimeSlot`) y agenda pública. Incluye validaciones: obligatorios, longitudes, formatos, `birth_date` no futura, motivo obligatorio, `is_active` explícito al editar.

- **`app/services/`** (carpeta, un módulo por dominio) —

- `slots.py`: cálculo de los 16 turnos, cruce con citas no canceladas, domingo, turnos transcurridos.

- `specialties.py`: normalización y unicidad.

- `doctors.py`: unicidad de licencia, filtros, desactivación con citas SCHEDULED futuras.

- `patients.py`: unicidad de cédula, búsqueda por cédula/nombre, desactivación con citas futuras.

- `appointments.py`: validación de turno, solapamientos médico/paciente, activo del médico y paciente, transiciones de estado y observaciones.

- `public_schedule.py`: proyección sin datos sensibles.

- **`app/routers/`** (carpeta) — `auth.py`, `specialties.py`, `doctors.py`, `patients.py`, `appointments.py`, `public_schedule.py`. Cada uno con sus endpoints y la dependencia `CurrentAdminId` (excepto login y agenda pública).

- **`app/main.py`** (actualización) — incluir los routers bajo `/api`, registrar el `RequestValidationError` handler que devuelve `{"detail": "..."}` genérico en español, y dejar el mount de `static` al final.

Aparte (no backend): `README.md` con instrucciones para Windows.

Si prefieres un único `app/services.py` en lugar de la carpeta, dímelo y lo ajusto cuando toque.

---

### Usuario

La lista está bien y prefiero la carpeta services pero no veo un servicio para el login. Esto puede ocasionar que la lógica de verificar al admin y su contraseña quede en el router, y el diseño dice que los routers solo llaman a los servicios. Agrega services/auth.py.
Vamos con el login (RF-01). Genera schemas.py solo con los esquemas de auth por ahora, services/auth.py, routers/auth.py y el main.py actualizado.

---

### DeepSeek AI

**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
from pydantic import BaseModel, Field, field_validator

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
```
**`app/services/__init__.py`**

```python

```
**`app/services/auth.py`**

```python
"""Authentication service for the administrator."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Admin
from app.schemas import LoginRequest, LoginResponse
from app.security import create_access_token, verify_password

def authenticate(db: Session, username: str, password: str) -> Admin:
    admin = db.scalar(select(Admin).where(Admin.username == username))
    if admin is None or not verify_password(password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return admin

def login(db: Session, payload: LoginRequest) -> LoginResponse:
    admin = authenticate(db, payload.username, payload.password)
    token = create_access_token(admin.id)
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expiration_minutes * 60,
    )
```
**`app/routers/__init__.py`**

```python

```
**`app/routers/auth.py`**

```python
"""Authentication endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import LoginRequest, LoginResponse
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    return auth_service.login(db, payload)
```
**`app/main.py`**

```python
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

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```
**Decisiones:**

- El router es solo orquestación: recibe `LoginRequest`, delega en `auth_service.login` y devuelve `LoginResponse`. La verificación de credenciales vive en `authenticate()` del servicio.

- `login` responde 401 con `"Usuario o contraseña incorrectos."` (mismo mensaje para usuario inexistente y contraseña errónea, para no filtrar cuál falló) y cabecera `WWW-Authenticate: Bearer`.

- `LoginResponse` incluye `expires_in` en segundos, útil para que el frontend programe el logout; `token_type` sigue el estándar Bearer que ya usa `security.py`.

- Agregué el handler de `RequestValidationError` en `main.py` porque RNF-04 exige un 422 genérico en español; sin él, FastAPI devolvería su mensaje por defecto en inglés. Los routers se incluyen antes del `mount` de `static` para que `/api/*` tenga prioridad.

Prueba: `POST /api/auth/login` con `{"username": "admin", "password": "<la del .env>"}`. Debe devolver el token; con credenciales malas, 401; con body inválido, 422 genérico.

---

### Usuario

El login funcionó bien: devuelve el token, con contraseña incorrecta da 401 y sin contraseña da 422. Ahora vamos con especialidades (RF-02). Dame schemas.py completo con los esquemas de especialidades agregados, services/specialties.py, routers/specialties.py y main.py actualizado.

---

### DeepSeek AI

**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
from pydantic import BaseModel, ConfigDict, Field, field_validator

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(SpecialtyBase):
    pass

class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
```
**`app/services/specialties.py`**

```python
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
```
**`app/routers/specialties.py`**

```python
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
```
**`app/main.py`**

```python
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

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```
**Decisiones:**

- `normalized_name` nunca viene del cliente: el servicio lo recalcula con `normalize_name()` al crear y editar, y compara contra el índice único para devolver 409.

- `description` se normaliza a `None` si queda vacía tras `strip()`, para no guardar cadenas blancas.

- `SpecialtyRead` expone `id`, `name` y `description`, no el `normalized_name` interno.

- Los tres endpoints exigen `CurrentAdminId` (401 si falta el token) y el router solo delega; toda la lógica de unicidad y 404 está en el servicio.

---

### Usuario

Especialidades funcionó: protegido con token, crea, lista, edita, los duplicados sin tilde o en minúsculas dan 409 y el id inexistente da 404. También pude insertar desde DataGrip sin problemas. Ahora vamos con médicos (RF-03). Dame schemas.py completo con los esquemas de médicos agregados, services/doctors.py, routers/doctors.py y main.py actualizado.

---

### DeepSeek AI

**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(SpecialtyBase):
    pass

class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    specialty_id: int

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(DoctorBase):
    is_active: bool

class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    license_number: str
    phone: str | None
    email: str | None
    specialty_id: int
    specialty_name: str
    is_active: bool
```
**`app/services/doctors.py`**

```python
"""Doctor management service."""
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.config import TIMEZONE
from app.models import Appointment, AppointmentStatus, Doctor, Specialty
from app.schemas import DoctorCreate, DoctorUpdate

def list_doctors(
    db: Session,
    specialty_id: int | None = None,
    is_active: bool | None = None,
) -> list[Doctor]:
    stmt = (
        select(Doctor)
        .options(joinedload(Doctor.specialty))
        .order_by(Doctor.last_name, Doctor.first_name)
    )
    if specialty_id is not None:
        stmt = stmt.where(Doctor.specialty_id == specialty_id)
    if is_active is not None:
        stmt = stmt.where(Doctor.is_active == is_active)
    return list(db.scalars(stmt))

def _get(db: Session, doctor_id: int) -> Doctor:
    doctor = db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Médico no encontrado.",
        )
    return doctor

def _ensure_specialty(db: Session, specialty_id: int) -> None:
    if db.get(Specialty, specialty_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Especialidad no encontrada.",
        )

def _ensure_unique_license(
    db: Session, license_number: str, exclude_id: int | None = None
) -> None:
    stmt = select(Doctor).where(Doctor.license_number == license_number)
    if exclude_id is not None:
        stmt = stmt.where(Doctor.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un médico con ese número de registro.",
        )

def _future_scheduled_count(db: Session, doctor_id: int) -> int:
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    current_time = now.time()
    stmt = select(func.count(Appointment.id)).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status == AppointmentStatus.SCHEDULED.value,
        or_(
            Appointment.date > today,
            and_(Appointment.date == today, Appointment.start_time > current_time),
        ),
    )
    return db.scalar(stmt) or 0

def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    _ensure_specialty(db, payload.specialty_id)
    _ensure_unique_license(db, payload.license_number)
    doctor = Doctor(
        first_name=payload.first_name,
        last_name=payload.last_name,
        license_number=payload.license_number,
        phone=payload.phone,
        email=payload.email,
        specialty_id=payload.specialty_id,
        is_active=True,
    )
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

def update_doctor(db: Session, doctor_id: int, payload: DoctorUpdate) -> Doctor:
    doctor = _get(db, doctor_id)
    _ensure_specialty(db, payload.specialty_id)
    _ensure_unique_license(db, payload.license_number, exclude_id=doctor.id)

    if doctor.is_active and not payload.is_active:
        count = _future_scheduled_count(db, doctor.id)
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El médico tiene {count} cita(s) futura(s) agendada(s). "
                    "Debe cancelarlas antes de desactivarlo."
                ),
            )

    doctor.first_name = payload.first_name
    doctor.last_name = payload.last_name
    doctor.license_number = payload.license_number
    doctor.phone = payload.phone
    doctor.email = payload.email
    doctor.specialty_id = payload.specialty_id
    doctor.is_active = payload.is_active
    db.commit()
    db.refresh(doctor)
    return doctor
```
**`app/routers/doctors.py`**

```python
"""Doctor endpoints."""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor
from app.schemas import DoctorCreate, DoctorRead, DoctorUpdate
from app.security import CurrentAdminId
from app.services import doctors as service

router = APIRouter(prefix="/doctors", tags=["doctors"])

def _to_read(doctor: Doctor) -> DoctorRead:
    return DoctorRead(
        id=doctor.id,
        first_name=doctor.first_name,
        last_name=doctor.last_name,
        license_number=doctor.license_number,
        phone=doctor.phone,
        email=doctor.email,
        specialty_id=doctor.specialty_id,
        specialty_name=doctor.specialty.name,
        is_active=doctor.is_active,
    )

@router.get("", response_model=list[DoctorRead])
def list_doctors(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
    specialty_id: int | None = None,
    is_active: bool | None = None,
) -> list[DoctorRead]:
    doctors = service.list_doctors(db, specialty_id=specialty_id, is_active=is_active)
    return [_to_read(d) for d in doctors]

@router.post("", response_model=DoctorRead, status_code=201)
def create_doctor(
    payload: DoctorCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> DoctorRead:
    return _to_read(service.create_doctor(db, payload))

@router.put("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: int,
    payload: DoctorUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> DoctorRead:
    return _to_read(service.update_doctor(db, doctor_id, payload))
```
**`app/main.py`**

```python
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
```
**Decisiones:**

- `DoctorUpdate` exige `is_active: bool` sin default: si el cliente lo omite, 422 (así se cumple "enviarse siempre de forma explícita" de RF-03).

- La desactivación se bloquea solo si hay citas **futuras** `SCHEDULED` (fecha > hoy, o hoy con `start_time > hora actual` en `America/Guayaquil`); una cita ya transcurrida no impide desactivar, coherente con el texto de RF-03.

- `DoctorRead` expande `specialty_name` desde la relación; el listado usa `joinedload(Doctor.specialty)` para evitar N+1.

- `specialty_id` inexistente devuelve 404 tanto en crear como en editar; la validación de email usa un regex ligero, sin agregar `email-validator` a las dependencias.

---

### Usuario

Médicos funcionó bien: lista con el nombre de la especialidad, crea, el registro duplicado da 409, la especialidad inexistente 404, al cambiar de especialidad la respuesta muestra la nueva, sin is_active da 422 y la desactivación con citas futuras da 409 con la cantidad.

Te adjunto el diseño actualizado. Cambió un punto de la sección 12: la API devuelve nombres y apellidos por separado, también en citas y en la agenda pública, y el frontend los arma como "Apellidos Nombres". Ténlo en cuenta de aquí en adelante.

Ahora vamos con pacientes (RF-04 y RF-05). Dame schemas.py completo con los esquemas de pacientes agregados, services/patients.py, routers/patients.py y main.py actualizado.

---

### DeepSeek AI

**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(SpecialtyBase):
    pass

class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    specialty_id: int

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(DoctorBase):
    is_active: bool

class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    license_number: str
    phone: str | None
    email: str | None
    specialty_id: int
    specialty_name: str
    is_active: bool

class PatientBase(BaseModel):
    national_id: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    phone: str = Field(min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=150)

    @field_validator("national_id", "first_name", "last_name", "phone")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

    @field_validator("birth_date")
    @classmethod
    def _no_future_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return v

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    is_active: bool

class PatientRead(BaseModel):
    id: int
    national_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    phone: str
    email: str | None
    is_active: bool
```
**`app/services/patients.py`**

```python
"""Patient management service."""
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.config import TIMEZONE
from app.models import Appointment, AppointmentStatus, Patient, normalize_name
from app.schemas import PatientCreate, PatientUpdate

def list_patients(
    db: Session,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Patient]:
    stmt = select(Patient).order_by(Patient.last_name, Patient.first_name)
    if is_active is not None:
        stmt = stmt.where(Patient.is_active == is_active)
    patients = list(db.scalars(stmt))
    if search and search.strip():
        query = search.strip()
        normalized_query = normalize_name(query)
        patients = [
            p for p in patients
            if query in p.national_id
            or normalized_query in normalize_name(p.first_name)
            or normalized_query in normalize_name(p.last_name)
        ]
    return patients

def _get(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado.",
        )
    return patient

def _ensure_unique_national_id(
    db: Session, national_id: str, exclude_id: int | None = None
) -> None:
    stmt = select(Patient).where(Patient.national_id == national_id)
    if exclude_id is not None:
        stmt = stmt.where(Patient.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un paciente con esa cédula.",
        )

def _future_scheduled_count(db: Session, patient_id: int) -> int:
    now = datetime.now(ZoneInfo(TIMEZONE))
    today = now.date()
    current_time = now.time()
    stmt = select(func.count(Appointment.id)).where(
        Appointment.patient_id == patient_id,
        Appointment.status == AppointmentStatus.SCHEDULED.value,
        or_(
            Appointment.date > today,
            and_(Appointment.date == today, Appointment.start_time > current_time),
        ),
    )
    return db.scalar(stmt) or 0

def create_patient(db: Session, payload: PatientCreate) -> Patient:
    _ensure_unique_national_id(db, payload.national_id)
    patient = Patient(
        national_id=payload.national_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        birth_date=payload.birth_date,
        phone=payload.phone,
        email=payload.email,
        is_active=True,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient

def update_patient(db: Session, patient_id: int, payload: PatientUpdate) -> Patient:
    patient = _get(db, patient_id)
    _ensure_unique_national_id(db, payload.national_id, exclude_id=patient.id)

    if patient.is_active and not payload.is_active:
        count = _future_scheduled_count(db, patient.id)
        if count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"El paciente tiene {count} cita(s) futura(s) agendada(s). "
                    "Debe cancelarlas antes de desactivarlo."
                ),
            )

    patient.national_id = payload.national_id
    patient.first_name = payload.first_name
    patient.last_name = payload.last_name
    patient.birth_date = payload.birth_date
    patient.phone = payload.phone
    patient.email = payload.email
    patient.is_active = payload.is_active
    db.commit()
    db.refresh(patient)
    return patient
```
**`app/routers/patients.py`**

```python
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
```
**`app/main.py`**

```python
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
from app.routers import patients as patients_router
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
app.include_router(patients_router.router, prefix="/api")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```
**Decisiones:**

- La búsqueda (`search`) se hace en Python tras filtrar por `is_active`: `national_id` con substring literal, nombres con `normalize_name()` para que "perez" encuentre "Pérez". Es coherente con RNF-04 ("sin paginación por volumen reducido").

- `birth_date` es opcional y no puede ser futura; `is_active` es obligatorio en `PatientUpdate` (igual que en médicos, para no reactivar sin querer).

- La desactivación bloquea solo si hay citas **futuras** `SCHEDULED` (`date > hoy`, o `hoy` con `start_time > hora actual` en Guayaquil), con el mismo patrón que médicos.

- `PatientRead` devuelve `first_name`/`last_name` por separado (según sección 12 actualizada); el frontend arma "Apellidos Nombres".

---

### Usuario

Pacientes funcionó bien: crea, la cédula duplicada da 409, la fecha futura y la falta de teléfono dan 422, la búsqueda por cédula o por apellido sin tilde funciona, sin is_active da 422 y la desactivación con citas futuras da 409.
Ahora vamos con la disponibilidad (RF-06). Dame schemas.py completo con lo necesario, services/slots.py y routers/doctors.py con el endpoint de disponibilidad agregado.

---

### DeepSeek AI

**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
import re
from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(SpecialtyBase):
    pass

class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    specialty_id: int

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(DoctorBase):
    is_active: bool

class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    license_number: str
    phone: str | None
    email: str | None
    specialty_id: int
    specialty_name: str
    is_active: bool

class PatientBase(BaseModel):
    national_id: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    phone: str = Field(min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=150)

    @field_validator("national_id", "first_name", "last_name", "phone")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

    @field_validator("birth_date")
    @classmethod
    def _no_future_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return v

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    is_active: bool

class PatientRead(BaseModel):
    id: int
    national_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    phone: str
    email: str | None
    is_active: bool

class TimeSlotRead(BaseModel):
    start_time: time
    end_time: time
    available: bool
    appointment_id: int | None = None
    status: str | None = None
```
**`app/services/slots.py`**

```python
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
    while t  list[TimeSlotRead]:
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
        if target_date **`app/routers/doctors.py`**

```python
"""Doctor endpoints."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Doctor
from app.schemas import DoctorCreate, DoctorRead, DoctorUpdate, TimeSlotRead
from app.security import CurrentAdminId
from app.services import doctors as service
from app.services import slots as slots_service

router = APIRouter(prefix="/doctors", tags=["doctors"])

def _to_read(doctor: Doctor) -> DoctorRead:
    return DoctorRead(
        id=doctor.id,
        first_name=doctor.first_name,
        last_name=doctor.last_name,
        license_number=doctor.license_number,
        phone=doctor.phone,
        email=doctor.email,
        specialty_id=doctor.specialty_id,
        specialty_name=doctor.specialty.name,
        is_active=doctor.is_active,
    )

@router.get("", response_model=list[DoctorRead])
def list_doctors(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
    specialty_id: int | None = None,
    is_active: bool | None = None,
) -> list[DoctorRead]:
    doctors = service.list_doctors(db, specialty_id=specialty_id, is_active=is_active)
    return [_to_read(d) for d in doctors]

@router.post("", response_model=DoctorRead, status_code=201)
def create_doctor(
    payload: DoctorCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> DoctorRead:
    return _to_read(service.create_doctor(db, payload))

@router.put("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: int,
    payload: DoctorUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> DoctorRead:
    return _to_read(service.update_doctor(db, doctor_id, payload))

@router.get("/{doctor_id}/availability", response_model=list[TimeSlotRead])
def get_availability(
    doctor_id: int,
    date: date,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> list[TimeSlotRead]:
    return slots_service.get_availability(db, doctor_id, date)
```
**Decisiones:**

- `services/slots.py` define `business_slots()` y `add_minutes()` como helpers públicos; `seed.py` aún tiene sus propias copias privadas. Cuando toque limpiar, conviene que `seed.py` importe de aquí, pero no lo toqué sin pedirlo.

- Domingo → `200` con lista vacía (sección 12), sin consultar la base. Fecha pasada → 16 turnos con `available=false`; turno hoy ya transcurrido (`start_time <= current_time`) → `available=false`. Ambos casos conservan `appointment_id`/`status` si hubiera cita, para que el admin vea el historial.

- `available` es `true` solo si el turno es futuro **y** no tiene cita no cancelada. El filtro `status != 'CANCELLED'` en la query garantiza que una cita cancelada no ocupa el turno.

- Médico inactivo → `400`; médico inexistente → `404`; el orden es `404` primero. `GET /{doctor_id}/availability` no choca con `PUT /{doctor_id}` porque Starlette compara por número de segmentos.

---

### Usuario

La disponibilidad funcionó bien: 16 turnos sin el almuerzo, los transcurridos no disponibles, los ocupados con su estado, el domingo vacío, el médico desactivado da 400 y el inexistente 404.
Ahora vamos con las citas (RF-07, RF-08 y RF-09). Dame schemas.py completo con los esquemas de citas agregados, services/appointments.py, routers/appointments.py y main.py actualizado.

---

### DeepSeek AI

**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
import re
from datetime import date, datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import AppointmentStatus

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(SpecialtyBase):
    pass

class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    specialty_id: int

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(DoctorBase):
    is_active: bool

class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    license_number: str
    phone: str | None
    email: str | None
    specialty_id: int
    specialty_name: str
    is_active: bool

class PatientBase(BaseModel):
    national_id: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    phone: str = Field(min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=150)

    @field_validator("national_id", "first_name", "last_name", "phone")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

    @field_validator("birth_date")
    @classmethod
    def _no_future_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return v

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    is_active: bool

class PatientRead(BaseModel):
    id: int
    national_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    phone: str
    email: str | None
    is_active: bool

class TimeSlotRead(BaseModel):
    start_time: time
    end_time: time
    available: bool
    appointment_id: int | None = None
    status: str | None = None

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    start_time: time
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El motivo es obligatorio.")
        return v

class AppointmentUpdate(BaseModel):
    status: AppointmentStatus | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _require_any_field(self) -> "AppointmentUpdate":
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        return self

class AppointmentRead(BaseModel):
    id: int
    patient_id: int
    patient_first_name: str
    patient_last_name: str
    doctor_id: int
    doctor_first_name: str
    doctor_last_name: str
    specialty_id: int
    specialty_name: str
    date: date
    start_time: time
    end_time: time
    reason: str
    status: str
    notes: str | None
    created_at: datetime
```
**`app/services/appointments.py`**

```python
"""Appointment management service."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import BUSINESS_DAYS, SLOT_DURATION_MINUTES, TIMEZONE
from app.models import Appointment, AppointmentStatus, Doctor, Patient
from app.schemas import AppointmentCreate, AppointmentUpdate
from app.services.slots import add_minutes, business_slots

def _now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))

def _has_started(target_date: date, start_time: time, now: datetime) -> bool:
    if target_date  now.date():
        return False
    return start_time  None:
    if target_date.weekday() not in BUSINESS_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El centro no atiende ese día.",
        )
    if start_time not in business_slots():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El turno seleccionado no es válido.",
        )

def _check_doctor_conflict(
    db: Session, doctor_id: int, target_date: date, start_time: time
) -> None:
    exists = db.scalar(
        select(Appointment.id).where(
            Appointment.doctor_id == doctor_id,
            Appointment.date == target_date,
            Appointment.start_time == start_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El médico ya tiene una cita en ese turno.",
        )

def _check_patient_conflict(
    db: Session, patient_id: int, target_date: date, start_time: time
) -> None:
    exists = db.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient_id,
            Appointment.date == target_date,
            Appointment.start_time == start_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente ya tiene una cita en ese turno.",
        )

def list_appointments(
    db: Session,
    doctor_id: int | None = None,
    specialty_id: int | None = None,
    patient_id: int | None = None,
    target_date: date | None = None,
    status_filter: AppointmentStatus | None = None,
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.specialty),
        )
        .order_by(Appointment.date, Appointment.start_time)
    )
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if specialty_id is not None:
        stmt = stmt.where(Appointment.doctor.has(Doctor.specialty_id == specialty_id))
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if target_date is not None:
        stmt = stmt.where(Appointment.date == target_date)
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter.value)
    return list(db.scalars(stmt))

def create_appointment(db: Session, payload: AppointmentCreate) -> Appointment:
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado.",
        )
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente está desactivado.",
        )

    doctor = db.get(Doctor, payload.doctor_id)
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

    _validate_slot(payload.date, payload.start_time)

    if _has_started(payload.date, payload.start_time, _now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede agendar una cita en una fecha u hora pasada.",
        )

    _check_doctor_conflict(db, payload.doctor_id, payload.date, payload.start_time)
    _check_patient_conflict(db, payload.patient_id, payload.date, payload.start_time)

    appointment = Appointment(
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=add_minutes(payload.start_time, SLOT_DURATION_MINUTES),
        reason=payload.reason,
        status=AppointmentStatus.SCHEDULED.value,
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El turno seleccionado ya está ocupado.",
        )
    db.refresh(appointment)
    return appointment

def update_appointment(
    db: Session, appointment_id: int, payload: AppointmentUpdate
) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada.",
        )

    if payload.status is not None:
        new_status = payload.status.value
        if new_status != appointment.status:
            if appointment.status != AppointmentStatus.SCHEDULED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Solo se puede cambiar el estado de una cita SCHEDULED.",
                )
            if new_status == AppointmentStatus.CANCELLED.value:
                appointment.cancel()
            else:
                if not _has_started(appointment.date, appointment.start_time, _now()):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Solo se puede marcar ATTENDED o NO_SHOW cuando "
                            "ya llegó la hora de inicio de la cita."
                        ),
                    )
                if new_status == AppointmentStatus.ATTENDED.value:
                    appointment.mark_attended()
                else:
                    appointment.mark_no_show()

    if "notes" in payload.model_fields_set:
        appointment.notes = payload.notes

    db.commit()
    db.refresh(appointment)
    return appointment
```
**`app/routers/appointments.py`**

```python
"""Appointment endpoints."""
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Appointment, AppointmentStatus
from app.schemas import AppointmentCreate, AppointmentRead, AppointmentUpdate
from app.security import CurrentAdminId
from app.services import appointments as service

router = APIRouter(prefix="/appointments", tags=["appointments"])

def _to_read(a: Appointment) -> AppointmentRead:
    return AppointmentRead(
        id=a.id,
        patient_id=a.patient_id,
        patient_first_name=a.patient.first_name,
        patient_last_name=a.patient.last_name,
        doctor_id=a.doctor_id,
        doctor_first_name=a.doctor.first_name,
        doctor_last_name=a.doctor.last_name,
        specialty_id=a.doctor.specialty_id,
        specialty_name=a.doctor.specialty.name,
        date=a.date,
        start_time=a.start_time,
        end_time=a.end_time,
        reason=a.reason,
        status=a.status,
        notes=a.notes,
        created_at=a.created_at,
    )

@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
    doctor_id: int | None = None,
    specialty_id: int | None = None,
    patient_id: int | None = None,
    target_date: date | None = Query(default=None, alias="date"),
    status_filter: AppointmentStatus | None = Query(default=None, alias="status"),
) -> list[AppointmentRead]:
    appointments = service.list_appointments(
        db,
        doctor_id=doctor_id,
        specialty_id=specialty_id,
        patient_id=patient_id,
        target_date=target_date,
        status_filter=status_filter,
    )
    return [_to_read(a) for a in appointments]

@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentRead:
    return _to_read(service.create_appointment(db, payload))

@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    _admin: CurrentAdminId,
    db: Annotated[Session, Depends(get_db)],
) -> AppointmentRead:
    return _to_read(service.update_appointment(db, appointment_id, payload))
```
**`app/main.py`**

```python
"""FastAPI entry point for MediCitas."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (register models with Base.metadata)
from app.config import PROJECT_ROOT
from app.database import Base, engine
from app.routers import appointments as appointments_router
from app.routers import auth as auth_router
from app.routers import doctors as doctors_router
from app.routers import patients as patients_router
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
app.include_router(patients_router.router, prefix="/api")
app.include_router(appointments_router.router, prefix="/api")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```
**Decisiones:**

- **Crear**: valida existencia (404), activo (400), día/slot válido (400), no pasado (400, misma regla que disponibilidad: `start_time <= now`), conflicto de médico y de paciente (409), y atrapa `IntegrityError` → 409 como red de seguridad de los índices únicos parciales.

- **Listar**: `joinedload` de paciente, médico y especialidad para evitar N+1; orden por `date, start_time`; `Query(alias="date")` en `target_date` para conservar el nombre del query param del diseño sin chocar con el tipo `date`.

- **Actualizar**: si el estado es igual al actual, no-op (sección 12); ATTENDED/NO_SHOW exigen que `now >= start`; CANCELLED se permite incluso si ya pasó la hora; `notes` se actualiza solo si viene en `model_fields_set` (así se puede distinguir "no enviado" de "enviar null para borrar"). El estado del modelo sigue siendo `str` en la respuesta.

- `AppointmentUpdate` requiere al menos un campo enviado (validado con `model_validator`); si llega vacío → 422.

---

### Usuario

Probé las citas y todo funciona: registrar con todas sus validaciones, los filtros, los cambios de estado y que una cita cancelada libera el turno. Solo un detalle: la sección 12 dice que las reglas de transición de estado estén en un solo lugar. Los métodos cancel, mark_attended y mark_no_show del modelo ya validan que la cita esté SCHEDULED, pero el servicio repite esa misma validación antes de llamarlos. Haz que el servicio use solo los métodos del modelo y convierta su error en 400. Dame el archivo completo.

---

### DeepSeek AI

**`app/services/appointments.py`**

```python
"""Appointment management service."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import BUSINESS_DAYS, SLOT_DURATION_MINUTES, TIMEZONE
from app.models import Appointment, AppointmentStatus, Doctor, Patient
from app.schemas import AppointmentCreate, AppointmentUpdate
from app.services.slots import add_minutes, business_slots

def _now() -> datetime:
    return datetime.now(ZoneInfo(TIMEZONE))

def _has_started(target_date: date, start_time: time, now: datetime) -> bool:
    if target_date  now.date():
        return False
    return start_time  None:
    if target_date.weekday() not in BUSINESS_DAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El centro no atiende ese día.",
        )
    if start_time not in business_slots():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El turno seleccionado no es válido.",
        )

def _check_doctor_conflict(
    db: Session, doctor_id: int, target_date: date, start_time: time
) -> None:
    exists = db.scalar(
        select(Appointment.id).where(
            Appointment.doctor_id == doctor_id,
            Appointment.date == target_date,
            Appointment.start_time == start_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El médico ya tiene una cita en ese turno.",
        )

def _check_patient_conflict(
    db: Session, patient_id: int, target_date: date, start_time: time
) -> None:
    exists = db.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient_id,
            Appointment.date == target_date,
            Appointment.start_time == start_time,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
    )
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El paciente ya tiene una cita en ese turno.",
        )

def list_appointments(
    db: Session,
    doctor_id: int | None = None,
    specialty_id: int | None = None,
    patient_id: int | None = None,
    target_date: date | None = None,
    status_filter: AppointmentStatus | None = None,
) -> list[Appointment]:
    stmt = (
        select(Appointment)
        .options(
            joinedload(Appointment.patient),
            joinedload(Appointment.doctor).joinedload(Doctor.specialty),
        )
        .order_by(Appointment.date, Appointment.start_time)
    )
    if doctor_id is not None:
        stmt = stmt.where(Appointment.doctor_id == doctor_id)
    if specialty_id is not None:
        stmt = stmt.where(Appointment.doctor.has(Doctor.specialty_id == specialty_id))
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    if target_date is not None:
        stmt = stmt.where(Appointment.date == target_date)
    if status_filter is not None:
        stmt = stmt.where(Appointment.status == status_filter.value)
    return list(db.scalars(stmt))

def create_appointment(db: Session, payload: AppointmentCreate) -> Appointment:
    patient = db.get(Patient, payload.patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado.",
        )
    if not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente está desactivado.",
        )

    doctor = db.get(Doctor, payload.doctor_id)
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

    _validate_slot(payload.date, payload.start_time)

    if _has_started(payload.date, payload.start_time, _now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede agendar una cita en una fecha u hora pasada.",
        )

    _check_doctor_conflict(db, payload.doctor_id, payload.date, payload.start_time)
    _check_patient_conflict(db, payload.patient_id, payload.date, payload.start_time)

    appointment = Appointment(
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=add_minutes(payload.start_time, SLOT_DURATION_MINUTES),
        reason=payload.reason,
        status=AppointmentStatus.SCHEDULED.value,
    )
    db.add(appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El turno seleccionado ya está ocupado.",
        )
    db.refresh(appointment)
    return appointment

def _apply_transition(action) -> None:
    try:
        action()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

def update_appointment(
    db: Session, appointment_id: int, payload: AppointmentUpdate
) -> Appointment:
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada.",
        )

    if payload.status is not None:
        new_status = payload.status.value
        if new_status != appointment.status:
            if new_status in (
                AppointmentStatus.ATTENDED.value,
                AppointmentStatus.NO_SHOW.value,
            ) and not _has_started(appointment.date, appointment.start_time, _now()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Solo se puede marcar ATTENDED o NO_SHOW cuando "
                        "ya llegó la hora de inicio de la cita."
                    ),
                )
            if new_status == AppointmentStatus.CANCELLED.value:
                _apply_transition(appointment.cancel)
            elif new_status == AppointmentStatus.ATTENDED.value:
                _apply_transition(appointment.mark_attended)
            else:
                _apply_transition(appointment.mark_no_show)

    if "notes" in payload.model_fields_set:
        appointment.notes = payload.notes

    db.commit()
    db.refresh(appointment)
    return appointment
```
**Decisiones:**

- El servicio ya no repite la comprobación "debe estar SCHEDULED": solo llama a `cancel()`, `mark_attended()` o `mark_no_show()`. Un `ValueError` del modelo se traduce a 400 con el mismo mensaje que emite el modelo.

- La comprobación temporal (`_has_started`) sigue en el servicio porque el modelo no conoce la hora actual ni la zona horaria; se ejecuta solo para ATTENDED/NO_SHOW y antes de invocar el método.

- Se mantiene el atajo "mismo estado → no-op" (`new_status != appointment.status`) que pide la sección 12; es una comparación, no una validación de transición, y evita que un no-op intente pasar por `cancel()`/`mark_*` y reciba un 400 espurio.

- `_apply_transition()` es el único punto que convierte `ValueError` en 400; si en el futuro se agregan más métodos de transición, basta con pasarlos por aquí.

---

### Usuario

Las pruebas de actualizar salieron bien también con el cambio y ahora el mensaje de error viene del modelo. Ahora vamos con lo último del backend: la agenda pública (RF-10). Dame security.py completo con la restricción por red interna, schemas.py completo con lo necesario, services/public_schedule.py, routers/public_schedule.py y main.py actualizado.

---

### DeepSeek AI

**`app/security.py`**

```python
"""Password hashing, JWT handling and internal-network restriction."""
from datetime import UTC, datetime, timedelta
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

ALGORITHM = "HS256"

_bearer_scheme = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

def create_access_token(admin_id: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expiration_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)

def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_admin_id(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Token de autenticación ausente.")
    try:
        payload = jwt.decode(
            credentials.credentials, settings.secret_key, algorithms=[ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("La sesión ha expirado. Inicie sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido.")
    sub = payload.get("sub")
    try:
        return int(sub)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise _unauthorized("Token inválido.")

CurrentAdminId = Annotated[int, Depends(get_current_admin_id)]

_IPAddress = IPv4Address | IPv6Address
_IPNetwork = IPv4Network | IPv6Network

def _parse_networks(raw: list[str]) -> list[_IPNetwork]:
    return [ip_network(entry, strict=False) for entry in raw]

_ALLOWED_NETWORKS: list[_IPNetwork] = _parse_networks(settings.internal_networks_list)

def _is_internal(client_ip: str) -> bool:
    try:
        addr = ip_address(client_ip)
    except ValueError:
        return False
    # Unmap IPv4-mapped IPv6 (e.g. ::ffff:127.0.0.1) before comparing.
    if isinstance(addr, IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    for network in _ALLOWED_NETWORKS:
        if addr.version == network.version and addr in network:
            return True
    return False

def require_internal_network(request: Request) -> None:
    client = request.client
    host = client.host if client is not None else ""
    if not host or not _is_internal(host):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La agenda pública solo está disponible desde la red "
                "interna del centro médico."
            ),
        )
```
**`app/schemas.py`**

```python
"""Pydantic schemas for request/response models."""
import re
from datetime import date, datetime, time

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import AppointmentStatus

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def _bcrypt_limit(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("La contraseña no puede exceder 72 bytes.")
        return v

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SpecialtyBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El nombre es obligatorio.")
        return v

    @field_validator("description")
    @classmethod
    def _strip_description(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

class SpecialtyCreate(SpecialtyBase):
    pass

class SpecialtyUpdate(SpecialtyBase):
    pass

class SpecialtyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None

class DoctorBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    license_number: str = Field(min_length=1, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=150)
    specialty_id: int

    @field_validator("first_name", "last_name", "license_number")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("phone")
    @classmethod
    def _strip_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

class DoctorCreate(DoctorBase):
    pass

class DoctorUpdate(DoctorBase):
    is_active: bool

class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    license_number: str
    phone: str | None
    email: str | None
    specialty_id: int
    specialty_name: str
    is_active: bool

class PatientBase(BaseModel):
    national_id: str = Field(min_length=1, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    phone: str = Field(min_length=1, max_length=20)
    email: str | None = Field(default=None, max_length=150)

    @field_validator("national_id", "first_name", "last_name", "phone")
    @classmethod
    def _strip_required(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Este campo es obligatorio.")
        return v

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _EMAIL_RE.match(v):
            raise ValueError("Formato de email inválido.")
        return v

    @field_validator("birth_date")
    @classmethod
    def _no_future_birth_date(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura.")
        return v

class PatientCreate(PatientBase):
    pass

class PatientUpdate(PatientBase):
    is_active: bool

class PatientRead(BaseModel):
    id: int
    national_id: str
    first_name: str
    last_name: str
    birth_date: date | None
    phone: str
    email: str | None
    is_active: bool

class TimeSlotRead(BaseModel):
    start_time: time
    end_time: time
    available: bool
    appointment_id: int | None = None
    status: str | None = None

class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    date: date
    start_time: time
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("El motivo es obligatorio.")
        return v

class AppointmentUpdate(BaseModel):
    status: AppointmentStatus | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _require_any_field(self) -> "AppointmentUpdate":
        if not self.model_fields_set:
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        return self

class AppointmentRead(BaseModel):
    id: int
    patient_id: int
    patient_first_name: str
    patient_last_name: str
    doctor_id: int
    doctor_first_name: str
    doctor_last_name: str
    specialty_id: int
    specialty_name: str
    date: date
    start_time: time
    end_time: time
    reason: str
    status: str
    notes: str | None
    created_at: datetime

class PublicScheduleItemRead(BaseModel):
    date: date
    start_time: time
    end_time: time
    doctor_first_name: str
    doctor_last_name: str
    specialty_name: str
    patient_first_name: str
    patient_last_name: str
```
**`app/services/public_schedule.py`**

```python
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
```
**`app/routers/public_schedule.py`**

```python
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
```
**`app/main.py`**

```python
"""FastAPI entry point for MediCitas."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (register models with Base.metadata)
from app.config import PROJECT_ROOT
from app.database import Base, engine
from app.routers import appointments as appointments_router
from app.routers import auth as auth_router
from app.routers import doctors as doctors_router
from app.routers import patients as patients_router
from app.routers import public_schedule as public_schedule_router
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
app.include_router(patients_router.router, prefix="/api")
app.include_router(appointments_router.router, prefix="/api")
app.include_router(public_schedule_router.router, prefix="/api")

app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
```
**Decisiones:**

- `_ALLOWED_NETWORKS` se calcula una vez al importar; si el `.env` cambia hay que reiniciar, igual que el resto de `Settings`. Se usa `ip_network(..., strict=False)` para aceptar tanto `10.0.0.0/8` como `127.0.0.1`.

- La IP se toma de `request.client.host`, sin mirar cabeceras. Se desempaqueta `::ffff:a.b.c.d` a su IPv4 subyacente, que es lo que aparecerá en Windows al conectar a `127.0.0.1` por un socket IPv6.

- La restricción se declara como `dependencies=[Depends(require_internal_network)]` a nivel de router, así cualquier endpoint futuro bajo `/public-schedule` queda cubierto sin repetirla.

- `date` ausente → hoy en `America/Guayaquil` (no UTC). Solo se devuelven citas `SCHEDULED`; el schema no expone cédula, teléfono, motivo ni observaciones. Nombres y apellidos van por separado (sección 12).

---

### Usuario

El backend está terminado. La restricción por red de la agenda pública la dejo pendiente para el final. Ahora vamos con el frontend. Antes de generar código, dime en una lista corta qué archivos va a tener la carpeta static y qué hace cada uno.

---

### DeepSeek AI

**`static/`** — archivos propuestos:

Comunes

- `css/styles.css` — hoja de estilos única (layout, formularios, tablas, mensajes de error/éxito, modal).

- `js/api.js` — módulo común: `apiGet/apiPost/apiPut/apiPatch` sobre `fetch` con token en `Authorization`, parseo de `{detail}`, redirección a `/login.html` ante 401, y helpers `escapeHtml()` y `formatName(first, last)` → "Apellidos Nombres" (sección 12).

Páginas públicas

- `index.html` — agenda pública (red interna, sin login). Filtro por médico y fecha, hoy por defecto.

- `js/index.js` — lógica de la agenda pública.

- `login.html` — formulario de ingreso.

- `js/login.js` — login, guarda token en `sessionStorage`, redirige a `/admin/appointments.html`.

Panel de administración

- `admin/specialties.html` + `js/specialties.js` — listar, crear, editar.

- `admin/doctors.html` + `js/doctors.js` — listar con filtros (especialidad, estado), crear, editar (incluye `is_active`).

- `admin/patients.html` + `js/patients.js` — buscador, filtro por estado, crear, editar (incluye `is_active`).

- `admin/appointments.html` + `js/appointments.js` — filtros múltiples, tabla, cambio de estado y modal de observaciones (sección 12).

- `admin/new-appointment.html` + `js/new-appointment.js` — paciente (buscador), médico, fecha, grilla de turnos, motivo.

**Dos dudas antes de codificar:**

- **Navegación del panel**: el diseño no la especifica. ¿Agrego un menú fijo (Citas · Nueva cita · Pacientes · Médicos · Especialidades · Cerrar sesión) inyectado por un pequeño `js/admin-nav.js` común, o lo copio a mano en cada HTML? Lo primero evita duplicar HTML; lo segundo se queda estrictamente con "una página HTML por pantalla, un script por página" sin módulos extra.

- **Redirección tras login**: ¿siempre a `/admin/appointments.html`, o a la pantalla de admin desde la que se redirigió por falta de token? Lo primero es más simple; lo segundo requiere guardar `location.pathname` antes de redirigir.

---

### Usuario

1. Usa un admin-nav.js común, así el menú no se repite en cada página.
2. Siempre a /admin/appointments.html.
Empecemos por lo común y el login: css/styles.css, js/api.js, js/admin-nav.js, login.html y js/login.js.

---

### DeepSeek AI

**`static/css/styles.css`**

```css
*,
*::before,
*::after { box-sizing: border-box; }

:root {
    --color-bg: #f4f6f8;
    --color-surface: #ffffff;
    --color-border: #d0d7de;
    --color-text: #1f2933;
    --color-muted: #6b7280;
    --color-primary: #2563eb;
    --color-primary-hover: #1d4ed8;
    --color-danger: #dc2626;
    --color-danger-hover: #b91c1c;
    --radius: 6px;
}

html, body { margin: 0; padding: 0; }

body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.45;
    color: var(--color-text);
    background: var(--color-bg);
    min-width: 1280px;
}

h1, h2, h3 { margin-top: 0; }
h1 { font-size: 1.5rem; }
h2 { font-size: 1.2rem; }

a { color: var(--color-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

.muted { color: var(--color-muted); }

/* Container */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
}
.page-header h1 { margin: 0; }

/* Admin nav */
.admin-nav {
    display: flex;
    align-items: center;
    gap: 24px;
    background: #111827;
    color: #ffffff;
    padding: 0 24px;
    height: 56px;
}
.admin-nav .nav-brand { font-weight: 600; font-size: 1.05rem; }
.admin-nav .nav-links { display: flex; gap: 4px; flex: 1; }
.admin-nav .nav-link {
    color: #d1d5db;
    padding: 8px 12px;
    border-radius: var(--radius);
}
.admin-nav .nav-link:hover { background: #1f2937; text-decoration: none; }
.admin-nav .nav-link.active { background: #1f2937; color: #ffffff; }
.admin-nav .nav-logout {
    font: inherit;
    background: transparent;
    color: #d1d5db;
    border: 1px solid #374151;
    padding: 6px 12px;
    border-radius: var(--radius);
    cursor: pointer;
}
.admin-nav .nav-logout:hover { background: #1f2937; color: #ffffff; }

/* Buttons */
.btn {
    font: inherit;
    font-weight: 500;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    cursor: pointer;
    background: #e5e7eb;
    color: var(--color-text);
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary { background: var(--color-primary); color: #ffffff; }
.btn-primary:hover:not(:disabled) { background: var(--color-primary-hover); }
.btn-secondary { background: #e5e7eb; }
.btn-secondary:hover:not(:disabled) { background: #d1d5db; }
.btn-danger { background: var(--color-danger); color: #ffffff; }
.btn-danger:hover:not(:disabled) { background: var(--color-danger-hover); }
.btn-sm { padding: 4px 10px; font-size: 0.9rem; }

/* Forms */
.form-group { display: flex; flex-direction: column; margin-bottom: 14px; }
.form-group label { font-weight: 500; margin-bottom: 4px; }
.required { color: var(--color-danger); }
.form-group input,
.form-group select,
.form-group textarea {
    font: inherit;
    padding: 8px 10px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text);
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: -1px;
    border-color: var(--color-primary);
}
.form-group.has-error input,
.form-group.has-error select,
.form-group.has-error textarea { border-color: var(--color-danger); }
.field-error {
    color: var(--color-danger);
    font-size: 0.85rem;
    margin: 4px 0 0;
    min-height: 1em;
}
.field-error:empty { display: none; }

.form-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
}
.form-actions { display: flex; gap: 8px; margin-top: 16px; }

/* Alerts */
.alert {
    padding: 10px 14px;
    border-radius: var(--radius);
    margin: 12px 0;
    font-size: 0.95rem;
}
.alert[hidden] { display: none; }
.alert-error   { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.alert-success { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.alert-info    { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }

/* Tables */
.table-wrap {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    overflow: hidden;
}
table { width: 100%; border-collapse: collapse; }
th, td {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--color-border);
    vertical-align: top;
}
th {
    background: #f9fafb;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #f9fafb; }

/* Badges (estados de cita) */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-SCHEDULED { background: #dbeafe; color: #1e40af; }
.badge-CANCELLED { background: #f3f4f6; color: #4b5563; }
.badge-ATTENDED  { background: #dcfce7; color: #166534; }
.badge-NO_SHOW   { background: #fef3c7; color: #92400e; }

/* Login */
body.login-page {
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
}
.login-card {
    width: 380px;
    padding: 32px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}
.login-card h1 { margin-bottom: 4px; }
.login-card .muted { margin-top: 0; margin-bottom: 24px; }
.login-card .btn { width: 100%; padding: 10px; margin-top: 4px; }

/* Modal (usado en la pantalla de citas) */
.modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 50;
}
.modal-backdrop[hidden] { display: none; }
.modal {
    width: 480px;
    max-width: 90vw;
    background: var(--color-surface);
    border-radius: var(--radius);
    padding: 24px;
}
.modal h2 { margin-top: 0; }
```
**`static/js/api.js`**

```js
// Common API client and small helpers shared by all pages.

const TOKEN_KEY = "medicitas_token";

export function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    sessionStorage.removeItem(TOKEN_KEY);
}

async function request(method, path, body, options) {
    const opts = options || {};
    const redirectOn401 = opts.redirectOn401 !== false;

    const headers = {};
    if (body !== undefined) {
        headers["Content-Type"] = "application/json";
    }
    const token = getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let response;
    try {
        response = await fetch(path, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    } catch {
        throw new Error("No se pudo conectar con el servidor.");
    }

    if (response.status === 401 && token && redirectOn401) {
        clearToken();
        window.location.replace("/login.html");
        throw new Error("Sesión expirada.");
    }

    const text = await response.text();
    let data = null;
    if (text) {
        try { data = JSON.parse(text); } catch { data = null; }
    }

    if (!response.ok) {
        const detail = data && data.detail ? String(data.detail) : `Error ${response.status}.`;
        throw new Error(detail);
    }
    return data;
}

export function apiGet(path, options) {
    return request("GET", path, undefined, options);
}
export function apiPost(path, body, options) {
    return request("POST", path, body, options);
}
export function apiPut(path, body, options) {
    return request("PUT", path, body, options);
}
export function apiPatch(path, body, options) {
    return request("PATCH", path, body, options);
}

export function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replaceAll("&", "&")
        .replaceAll("", ">")
        .replaceAll('"', """)
        .replaceAll("'", "'");
}

// "Apellidos Nombres" (sección 12).
export function formatName(firstName, lastName) {
    return [lastName, firstName]
        .filter((part) => part && String(part).trim())
        .join(" ")
        .trim();
}
```
**`static/js/admin-nav.js`**

```js
// Auth guard + common admin navigation bar.
// Call initAdminPage() once at the top of each admin page script:
//   if (!initAdminPage()) throw new Error("Redirecting to login");

import { clearToken, getToken } from "./api.js";

const NAV_ITEMS = [
    { href: "/admin/appointments.html",     label: "Citas" },
    { href: "/admin/new-appointment.html",  label: "Nueva cita" },
    { href: "/admin/patients.html",         label: "Pacientes" },
    { href: "/admin/doctors.html",          label: "Médicos" },
    { href: "/admin/specialties.html",      label: "Especialidades" },
];

function buildNav() {
    const current = window.location.pathname;
    const nav = document.createElement("nav");
    nav.className = "admin-nav";

    const links = NAV_ITEMS.map((item) => {
        const cls = current === item.href ? "nav-link active" : "nav-link";
        return `${item.label}`;
    }).join("");

    nav.innerHTML = `
        MediCitas
        ${links}
        Cerrar sesión
    `;

    nav.querySelector("#nav-logout").addEventListener("click", () => {
        clearToken();
        window.location.replace("/login.html");
    });

    return nav;
}

export function initAdminPage() {
    if (!getToken()) {
        window.location.replace("/login.html");
        return false;
    }
    document.body.prepend(buildNav());
    return true;
}
```
**`static/login.html`**

```html

    Iniciar sesión · MediCitas

        MediCitas
        Acceso del administrador

                Usuario *

                Contraseña *

            Ingresar

```
**`static/js/login.js`**

```js
import { apiPost, setToken } from "./api.js";

const form = document.getElementById("login-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const formError = document.getElementById("form-error");
const submitBtn = document.getElementById("submit-btn");

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearErrors() {
    setFieldError("username", "");
    setFieldError("password", "");
    formError.hidden = true;
    formError.textContent = "";
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearErrors();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    let valid = true;
    if (!username) {
        setFieldError("username", "Ingrese su usuario.");
        valid = false;
    }
    if (!password) {
        setFieldError("password", "Ingrese su contraseña.");
        valid = false;
    }
    if (!valid) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Ingresando...";

    try {
        const data = await apiPost(
            "/api/auth/login",
            { username, password },
            { redirectOn401: false }
        );
        setToken(data.access_token);
        window.location.replace("/admin/appointments.html");
    } catch (err) {
        formError.textContent = err.message || "No se pudo iniciar sesión.";
        formError.hidden = false;
        submitBtn.disabled = false;
        submitBtn.textContent = "Ingresar";
    }
});
```
**Decisiones:**

- `api.js` es un módulo ES compartido; solo redirige a `/login.html` ante 401 cuando **hay** token (para no crear bucles en el login). `login.js` además pasa `redirectOn401: false` como salvaguarda.

- `admin-nav.js` expone `initAdminPage()` que (1) redirige si no hay token y (2) prepende la barra de navegación. Los scripts de cada página admin empiezan con `if (!initAdminPage()) throw new Error(...)` para cortar la ejecución cuando se redirige.

- Toda salida HTML pasa por `escapeHtml()`; `formatName()` aplica la convención "Apellidos Nombres" de la sección 12.

- `styles.css` cubre lo que usarán las próximas pantallas (tablas, badges de estado, modal, formularios con error por campo). El `body` de las páginas admin tiene `min-width: 1280px` según RNF-05; el login lo desactiva con `body.login-page`.

Prueba: abre `http://127.0.0.1:8000/login.html`. Credenciales malas → mensaje rojo; correctas → redirección a `/admin/appointments.html` (que aún no existe; verás 404 del mount, es lo esperado). Sin token, visitar cualquier `/admin/*.html` te llevará a login.

---

### Usuario

El login funciona: valida los campos vacíos, muestra el error con contraseña incorrecta sin recargar y con los datos correctos guarda el token y redirige. Ahora genera admin/specialties.html y js/specialties.js.

---

### DeepSeek AI

**`static/admin/specialties.html`**

```html

    Especialidades · MediCitas

            Especialidades

            Nueva especialidad

                        Nombre *

                        Descripción

                    Crear
                    Cancelar

            No hay especialidades registradas.

                            ID
                            Nombre
                            Descripción
                            Acciones

```
**`static/js/specialties.js`**

```js
import { apiGet, apiPost, apiPut, escapeHtml } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const form = document.getElementById("specialty-form");
const formTitle = document.getElementById("form-title");
const nameInput = document.getElementById("name");
const descriptionInput = document.getElementById("description");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("specialties-tbody");

let editingId = null;
let specialties = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function resetForm() {
    editingId = null;
    form.reset();
    setFieldError("name", "");
    setFieldError("description", "");
    formTitle.textContent = "Nueva especialidad";
    submitBtn.textContent = "Crear";
    cancelBtn.hidden = true;
    formError.hidden = true;
    formSuccess.hidden = true;
}

function showSuccess(message) {
    formSuccess.textContent = message;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
    formSuccess.hidden = true;
}

function validate() {
    let ok = true;
    setFieldError("name", "");
    setFieldError("description", "");

    const name = nameInput.value.trim();
    if (!name) {
        setFieldError("name", "El nombre es obligatorio.");
        ok = false;
    } else if (name.length > 100) {
        setFieldError("name", "El nombre no puede exceder 100 caracteres.");
        ok = false;
    }

    const description = descriptionInput.value.trim();
    if (description.length > 255) {
        setFieldError("description", "La descripción no puede exceder 255 caracteres.");
        ok = false;
    }
    return ok;
}

function renderTable() {
    if (specialties.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = specialties
        .map(
            (s) => `

            ${s.id}
            ${escapeHtml(s.name)}
            ${escapeHtml(s.description || "")}

                Editar

        `
        )
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const specialty = specialties.find((s) => s.id === id);
    if (!specialty) return;
    editingId = id;
    nameInput.value = specialty.name;
    descriptionInput.value = specialty.description || "";
    setFieldError("name", "");
    setFieldError("description", "");
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar especialidad #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    nameInput.focus();
}

async function loadSpecialties() {
    try {
        specialties = await apiGet("/api/specialties");
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar las especialidades.");
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;

    if (!validate()) return;

    const payload = {
        name: nameInput.value.trim(),
        description: descriptionInput.value.trim() || null,
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/specialties", payload);
            showSuccess("Especialidad creada.");
        } else {
            await apiPut(`/api/specialties/${editingId}`, payload);
            showSuccess("Especialidad actualizada.");
        }
        resetFormKeepMessage();
        await loadSpecialties();
    } catch (err) {
        showError(err.message || "No se pudo guardar la especialidad.");
    } finally {
        submitBtn.disabled = false;
    }
});

function resetFormKeepMessage() {
    const successText = formSuccess.textContent;
    const showSuccessMsg = !formSuccess.hidden;
    resetForm();
    if (showSuccessMsg) {
        formSuccess.textContent = successText;
        formSuccess.hidden = false;
    }
}

cancelBtn.addEventListener("click", () => {
    resetForm();
});

loadSpecialties();
```
**Decisiones:**

- Formulario único en modo crear/editar: al pulsar "Editar" en la fila, el formulario se rellena y cambia a "Guardar" con botón "Cancelar" visible. Al guardar, hace POST o PUT según `editingId`.

- `showSuccess()` se preserva tras `resetForm()` porque `resetForm()` limpia los mensajes; hay un pequeño `resetFormKeepMessage()` que restaura el mensaje de éxito para que el usuario lo vea después de la operación.

- Errores de API (409 por duplicado sin tildes, etc.) se muestran en el `alert-error` superior con el `detail` del backend.

- Validación de cliente replica las reglas del backend (nombre obligatorio y ≤100, descripción ≤255), y `escapeHtml()` se aplica a nombre y descripción al renderizar.

---

### Usuario

Especialidades funciona: el menú, crear, editar, cancelar, los duplicados muestran el error del backend y un nombre con HTML se muestra como texto. Ahora genera admin/doctors.html y js/doctors.js.

---

### DeepSeek AI

**`static/admin/doctors.html`**

```html

    Médicos · MediCitas

            Médicos

            Nuevo médico

                        Nombres *

                        Apellidos *

                        Registro profesional *

                        Especialidad *

                            — Seleccione —

                        Teléfono

                        Email

                        Activo

                    Crear
                    Cancelar

                    Filtrar por especialidad

                        Todas

                    Filtrar por estado

                        Todos
                        Activos
                        Inactivos

            No hay médicos con esos filtros.

                            Médico
                            Registro
                            Especialidad
                            Teléfono
                            Email
                            Estado
                            Acciones

```
**`static/js/doctors.js`**

```js
import { apiGet, apiPost, apiPut, escapeHtml, formatName } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const form = document.getElementById("doctor-form");
const formTitle = document.getElementById("form-title");
const firstNameInput = document.getElementById("first_name");
const lastNameInput = document.getElementById("last_name");
const licenseInput = document.getElementById("license_number");
const phoneInput = document.getElementById("phone");
const emailInput = document.getElementById("email");
const specialtySelect = document.getElementById("specialty_id");
const isActiveGroup = document.getElementById("is-active-group");
const isActiveInput = document.getElementById("is_active");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("doctors-tbody");
const filterSpecialty = document.getElementById("filter-specialty");
const filterActive = document.getElementById("filter-active");

let editingId = null;
let doctors = [];
let specialties = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearAllFieldErrors() {
    ["first_name", "last_name", "license_number", "specialty_id", "phone", "email", "is_active"]
        .forEach((f) => setFieldError(f, ""));
}

function resetForm() {
    editingId = null;
    form.reset();
    clearAllFieldErrors();
    isActiveGroup.hidden = true;
    isActiveInput.checked = false;
    formTitle.textContent = "Nuevo médico";
    submitBtn.textContent = "Crear";
    cancelBtn.hidden = true;
    formError.hidden = true;
    formSuccess.hidden = true;
}

function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
    formSuccess.hidden = true;
}

function showSuccess(message) {
    formSuccess.textContent = message;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function validate() {
    clearAllFieldErrors();
    let ok = true;

    const first = firstNameInput.value.trim();
    if (!first) { setFieldError("first_name", "Los nombres son obligatorios."); ok = false; }
    else if (first.length > 100) { setFieldError("first_name", "Máximo 100 caracteres."); ok = false; }

    const last = lastNameInput.value.trim();
    if (!last) { setFieldError("last_name", "Los apellidos son obligatorios."); ok = false; }
    else if (last.length > 100) { setFieldError("last_name", "Máximo 100 caracteres."); ok = false; }

    const license = licenseInput.value.trim();
    if (!license) { setFieldError("license_number", "El registro es obligatorio."); ok = false; }
    else if (license.length > 50) { setFieldError("license_number", "Máximo 50 caracteres."); ok = false; }

    if (!specialtySelect.value) { setFieldError("specialty_id", "Seleccione una especialidad."); ok = false; }

    const phone = phoneInput.value.trim();
    if (phone.length > 20) { setFieldError("phone", "Máximo 20 caracteres."); ok = false; }

    const email = emailInput.value.trim();
    if (email.length > 150) { setFieldError("email", "Máximo 150 caracteres."); ok = false; }
    else if (email && !EMAIL_RE.test(email)) { setFieldError("email", "Formato de email inválido."); ok = false; }

    return ok;
}

function renderTable() {
    if (doctors.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = doctors
        .map((d) => {
            const stateBadge = d.is_active
                ? 'Activo'
                : 'Inactivo';
            return `

                ${escapeHtml(formatName(d.first_name, d.last_name))}
                ${escapeHtml(d.license_number)}
                ${escapeHtml(d.specialty_name)}
                ${escapeHtml(d.phone || "")}
                ${escapeHtml(d.email || "")}
                ${stateBadge}

                    Editar

            `;
        })
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const doctor = doctors.find((d) => d.id === id);
    if (!doctor) return;
    editingId = id;
    firstNameInput.value = doctor.first_name;
    lastNameInput.value = doctor.last_name;
    licenseInput.value = doctor.license_number;
    phoneInput.value = doctor.phone || "";
    emailInput.value = doctor.email || "";
    specialtySelect.value = String(doctor.specialty_id);
    isActiveInput.checked = doctor.is_active;
    isActiveGroup.hidden = false;
    clearAllFieldErrors();
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar médico #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    firstNameInput.focus();
}

async function loadSpecialties() {
    try {
        specialties = await apiGet("/api/specialties");
        const optionsHtml = specialties
            .map((s) => `${escapeHtml(s.name)}`)
            .join("");
        specialtySelect.innerHTML = '— Seleccione —' + optionsHtml;
        filterSpecialty.innerHTML = 'Todas' + optionsHtml;
    } catch (err) {
        showError(err.message || "No se pudieron cargar las especialidades.");
    }
}

async function loadDoctors() {
    const params = new URLSearchParams();
    if (filterSpecialty.value) params.set("specialty_id", filterSpecialty.value);
    if (filterActive.value) params.set("is_active", filterActive.value);
    const query = params.toString();
    try {
        doctors = await apiGet(`/api/doctors${query ? "?" + query : ""}`);
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar los médicos.");
    }
}

function resetFormKeepMessage() {
    const successText = formSuccess.textContent;
    const showSuccessMsg = !formSuccess.hidden;
    resetForm();
    if (showSuccessMsg) {
        formSuccess.textContent = successText;
        formSuccess.hidden = false;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;

    if (!validate()) return;

    const payload = {
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        license_number: licenseInput.value.trim(),
        phone: phoneInput.value.trim() || null,
        email: emailInput.value.trim() || null,
        specialty_id: Number(specialtySelect.value),
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/doctors", payload);
            showSuccess("Médico creado.");
        } else {
            payload.is_active = isActiveInput.checked;
            await apiPut(`/api/doctors/${editingId}`, payload);
            showSuccess("Médico actualizado.");
        }
        resetFormKeepMessage();
        await loadDoctors();
    } catch (err) {
        showError(err.message || "No se pudo guardar el médico.");
    } finally {
        submitBtn.disabled = false;
    }
});

cancelBtn.addEventListener("click", () => resetForm());
filterSpecialty.addEventListener("change", loadDoctors);
filterActive.addEventListener("change", loadDoctors);

(async () => {
    await loadSpecialties();
    await loadDoctors();
})();
```
**Decisiones:**

- Formulario único crear/editar. El checkbox `is_active` solo se muestra al editar; al crear el backend siempre pone `true`, y en el payload de `PUT` se envía explícitamente (regla de la sección 12).

- Los filtros (`specialty_id`, `is_active`) llaman a `loadDoctors()` en cada cambio sin botón "Aplicar"; el backend ya soporta esos query params.

- El select de especialidad se rellena con `escapeHtml()` de los nombres; en el listado se muestra `formatName(first_name, last_name)` = "Apellidos Nombres".

- Los errores del backend (409 por registro duplicado, 404 por especialidad inexistente, 409 de desactivación con citas futuras) se muestran en el `alert-error` superior.

---

### Usuario

Encontré un error: al crear un médico se ve el checkbox "Activo" y según la lógica solo debería aparecer al editar. Corrígelo y dame los archivos que cambien completos.

---

### DeepSeek AI

El bug es CSS: `.form-group { display: flex; }` tiene mayor especificidad que la regla del user-agent `[hidden] { display: none; }`, así que el atributo `hidden` no oculta el bloque. Solo cambia `styles.css`.

**`static/css/styles.css`**

```css
*,
*::before,
*::after { box-sizing: border-box; }

[hidden] { display: none !important; }

:root {
    --color-bg: #f4f6f8;
    --color-surface: #ffffff;
    --color-border: #d0d7de;
    --color-text: #1f2933;
    --color-muted: #6b7280;
    --color-primary: #2563eb;
    --color-primary-hover: #1d4ed8;
    --color-danger: #dc2626;
    --color-danger-hover: #b91c1c;
    --radius: 6px;
}

html, body { margin: 0; padding: 0; }

body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.45;
    color: var(--color-text);
    background: var(--color-bg);
    min-width: 1280px;
}

h1, h2, h3 { margin-top: 0; }
h1 { font-size: 1.5rem; }
h2 { font-size: 1.2rem; }

a { color: var(--color-primary); text-decoration: none; }
a:hover { text-decoration: underline; }

.muted { color: var(--color-muted); }

/* Container */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}
.page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
}
.page-header h1 { margin: 0; }

/* Admin nav */
.admin-nav {
    display: flex;
    align-items: center;
    gap: 24px;
    background: #111827;
    color: #ffffff;
    padding: 0 24px;
    height: 56px;
}
.admin-nav .nav-brand { font-weight: 600; font-size: 1.05rem; }
.admin-nav .nav-links { display: flex; gap: 4px; flex: 1; }
.admin-nav .nav-link {
    color: #d1d5db;
    padding: 8px 12px;
    border-radius: var(--radius);
}
.admin-nav .nav-link:hover { background: #1f2937; text-decoration: none; }
.admin-nav .nav-link.active { background: #1f2937; color: #ffffff; }
.admin-nav .nav-logout {
    font: inherit;
    background: transparent;
    color: #d1d5db;
    border: 1px solid #374151;
    padding: 6px 12px;
    border-radius: var(--radius);
    cursor: pointer;
}
.admin-nav .nav-logout:hover { background: #1f2937; color: #ffffff; }

/* Buttons */
.btn {
    font: inherit;
    font-weight: 500;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-radius: var(--radius);
    cursor: pointer;
    background: #e5e7eb;
    color: var(--color-text);
}
.btn:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary { background: var(--color-primary); color: #ffffff; }
.btn-primary:hover:not(:disabled) { background: var(--color-primary-hover); }
.btn-secondary { background: #e5e7eb; }
.btn-secondary:hover:not(:disabled) { background: #d1d5db; }
.btn-danger { background: var(--color-danger); color: #ffffff; }
.btn-danger:hover:not(:disabled) { background: var(--color-danger-hover); }
.btn-sm { padding: 4px 10px; font-size: 0.9rem; }

/* Forms */
.form-group { display: flex; flex-direction: column; margin-bottom: 14px; }
.form-group label { font-weight: 500; margin-bottom: 4px; }
.required { color: var(--color-danger); }
.form-group input,
.form-group select,
.form-group textarea {
    font: inherit;
    padding: 8px 10px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text);
}
.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: -1px;
    border-color: var(--color-primary);
}
.form-group.has-error input,
.form-group.has-error select,
.form-group.has-error textarea { border-color: var(--color-danger); }
.field-error {
    color: var(--color-danger);
    font-size: 0.85rem;
    margin: 4px 0 0;
    min-height: 1em;
}
.field-error:empty { display: none; }

.form-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
}
.form-actions { display: flex; gap: 8px; margin-top: 16px; }

/* Alerts */
.alert {
    padding: 10px 14px;
    border-radius: var(--radius);
    margin: 12px 0;
    font-size: 0.95rem;
}
.alert-error   { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.alert-success { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.alert-info    { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }

/* Tables */
.table-wrap {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    overflow: hidden;
}
table { width: 100%; border-collapse: collapse; }
th, td {
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid var(--color-border);
    vertical-align: top;
}
th {
    background: #f9fafb;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--color-muted);
    text-transform: uppercase;
    letter-spacing: 0.03em;
}
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #f9fafb; }

/* Badges (estados de cita) */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.03em;
}
.badge-SCHEDULED { background: #dbeafe; color: #1e40af; }
.badge-CANCELLED { background: #f3f4f6; color: #4b5563; }
.badge-ATTENDED  { background: #dcfce7; color: #166534; }
.badge-NO_SHOW   { background: #fef3c7; color: #92400e; }

/* Login */
body.login-page {
    min-width: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
}
.login-card {
    width: 380px;
    padding: 32px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}
.login-card h1 { margin-bottom: 4px; }
.login-card .muted { margin-top: 0; margin-bottom: 24px; }
.login-card .btn { width: 100%; padding: 10px; margin-top: 4px; }

/* Modal (usado en la pantalla de citas) */
.modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 50;
}
.modal {
    width: 480px;
    max-width: 90vw;
    background: var(--color-surface);
    border-radius: var(--radius);
    padding: 24px;
}
.modal h2 { margin-top: 0; }
```
**Decisiones:**

- `[hidden] { display: none !important; }` al inicio del archivo: cualquier elemento con el atributo `hidden` se oculta, aunque otro selector (`display: flex`, `display: grid`, `display: block`, etc.) tenga mayor especificidad. Es la corrección correcta y evita que el mismo patrón se repita.

- Eliminé las reglas `.alert[hidden]` y `.modal-backdrop[hidden]` porque quedan cubiertas por la regla global; no cambian el comportamiento.

- `doctors.js` no necesita cambios: ya ponía `isActiveGroup.hidden = true` en el reset y `false` al editar; el problema era que el CSS impedía que `hidden` surtiera efecto.

---

### Usuario

Médicos funciona: crear, editar, cambiar de especialidad, los filtros, el registro duplicado y la desactivación con citas futuras muestran el error del backend. Ahora genera admin/patients.html y js/patients.js.

---

### DeepSeek AI

**`static/admin/patients.html`**

```html

    Pacientes · MediCitas

            Pacientes

            Nuevo paciente

                        Cédula *

                        Fecha de nacimiento

                        Nombres *

                        Apellidos *

                        Teléfono *

                        Email

                        Activo

                    Crear
                    Cancelar

                    Buscar por cédula o nombre

                    Filtrar por estado

                        Todos
                        Activos
                        Inactivos

            No se encontraron pacientes.

                            Cédula
                            Paciente
                            Nacimiento
                            Teléfono
                            Email
                            Estado
                            Acciones

```
**`static/js/patients.js`**

```js
import { apiGet, apiPost, apiPut, escapeHtml, formatName } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const form = document.getElementById("patient-form");
const formTitle = document.getElementById("form-title");
const nationalIdInput = document.getElementById("national_id");
const birthDateInput = document.getElementById("birth_date");
const firstNameInput = document.getElementById("first_name");
const lastNameInput = document.getElementById("last_name");
const phoneInput = document.getElementById("phone");
const emailInput = document.getElementById("email");
const isActiveGroup = document.getElementById("is-active-group");
const isActiveInput = document.getElementById("is_active");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("patients-tbody");
const searchInput = document.getElementById("search");
const filterActive = document.getElementById("filter-active");

let editingId = null;
let patients = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearAllFieldErrors() {
    ["national_id", "birth_date", "first_name", "last_name", "phone", "email", "is_active"]
        .forEach((f) => setFieldError(f, ""));
}

function resetForm() {
    editingId = null;
    form.reset();
    clearAllFieldErrors();
    isActiveGroup.hidden = true;
    isActiveInput.checked = false;
    formTitle.textContent = "Nuevo paciente";
    submitBtn.textContent = "Crear";
    cancelBtn.hidden = true;
    formError.hidden = true;
    formSuccess.hidden = true;
}

function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
    formSuccess.hidden = true;
}

function showSuccess(message) {
    formSuccess.textContent = message;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function validate() {
    clearAllFieldErrors();
    let ok = true;

    const nid = nationalIdInput.value.trim();
    if (!nid) { setFieldError("national_id", "La cédula es obligatoria."); ok = false; }
    else if (nid.length > 20) { setFieldError("national_id", "Máximo 20 caracteres."); ok = false; }

    const first = firstNameInput.value.trim();
    if (!first) { setFieldError("first_name", "Los nombres son obligatorios."); ok = false; }
    else if (first.length > 100) { setFieldError("first_name", "Máximo 100 caracteres."); ok = false; }

    const last = lastNameInput.value.trim();
    if (!last) { setFieldError("last_name", "Los apellidos son obligatorios."); ok = false; }
    else if (last.length > 100) { setFieldError("last_name", "Máximo 100 caracteres."); ok = false; }

    const phone = phoneInput.value.trim();
    if (!phone) { setFieldError("phone", "El teléfono es obligatorio."); ok = false; }
    else if (phone.length > 20) { setFieldError("phone", "Máximo 20 caracteres."); ok = false; }

    const email = emailInput.value.trim();
    if (email.length > 150) { setFieldError("email", "Máximo 150 caracteres."); ok = false; }
    else if (email && !EMAIL_RE.test(email)) { setFieldError("email", "Formato de email inválido."); ok = false; }

    const birth = birthDateInput.value;
    if (birth && birth > todayIso()) {
        setFieldError("birth_date", "La fecha de nacimiento no puede ser futura.");
        ok = false;
    }

    return ok;
}

function renderTable() {
    if (patients.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = patients
        .map((p) => {
            const stateBadge = p.is_active
                ? 'Activo'
                : 'Inactivo';
            return `

                ${escapeHtml(p.national_id)}
                ${escapeHtml(formatName(p.first_name, p.last_name))}
                ${escapeHtml(p.birth_date || "")}
                ${escapeHtml(p.phone)}
                ${escapeHtml(p.email || "")}
                ${stateBadge}

                    Editar

            `;
        })
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const patient = patients.find((p) => p.id === id);
    if (!patient) return;
    editingId = id;
    nationalIdInput.value = patient.national_id;
    birthDateInput.value = patient.birth_date || "";
    firstNameInput.value = patient.first_name;
    lastNameInput.value = patient.last_name;
    phoneInput.value = patient.phone;
    emailInput.value = patient.email || "";
    isActiveInput.checked = patient.is_active;
    isActiveGroup.hidden = false;
    clearAllFieldErrors();
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar paciente #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    nationalIdInput.focus();
}

async function loadPatients() {
    const params = new URLSearchParams();
    const search = searchInput.value.trim();
    if (search) params.set("search", search);
    if (filterActive.value) params.set("is_active", filterActive.value);
    const query = params.toString();
    try {
        patients = await apiGet(`/api/patients${query ? "?" + query : ""}`);
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar los pacientes.");
    }
}

function resetFormKeepMessage() {
    const successText = formSuccess.textContent;
    const showSuccessMsg = !formSuccess.hidden;
    resetForm();
    if (showSuccessMsg) {
        formSuccess.textContent = successText;
        formSuccess.hidden = false;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;

    if (!validate()) return;

    const payload = {
        national_id: nationalIdInput.value.trim(),
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        birth_date: birthDateInput.value || null,
        phone: phoneInput.value.trim(),
        email: emailInput.value.trim() || null,
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/patients", payload);
            showSuccess("Paciente creado.");
        } else {
            payload.is_active = isActiveInput.checked;
            await apiPut(`/api/patients/${editingId}`, payload);
            showSuccess("Paciente actualizado.");
        }
        resetFormKeepMessage();
        await loadPatients();
    } catch (err) {
        showError(err.message || "No se pudo guardar el paciente.");
    } finally {
        submitBtn.disabled = false;
    }
});

cancelBtn.addEventListener("click", () => resetForm());

let searchTimer = null;
searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadPatients, 250);
});
filterActive.addEventListener("change", loadPatients);

loadPatients();
```
**Decisiones:**

- Buscador con debounce de 250 ms sobre el endpoint `GET /api/patients?search=` (RF-05), filtro de estado con `is_active`; ambos pueden combinarse.

- `birth_date` opcional; si el usuario la ingresa, se valida contra `todayIso()` en el cliente (comparación lexicográfica ISO) y el backend la vuelve a validar. `type="date"` envía `yyyy-mm-dd`, formato que Pydantic acepta sin conversión.

- `is_active` oculto al crear (mismo patrón que médicos); en `PUT` se envía siempre explícito.

- Los errores del backend (409 cédula duplicada, 409 desactivación con citas futuras, 404) se muestran en el `alert-error` superior.

---

### Usuario

Pacientes funciona: crear, editar, la búsqueda mientras escribo, los filtros combinados, la cédula duplicada y la desactivación con citas futuras. Ahora genera admin/appointments.html y js/appointments.js.

---

### DeepSeek AI

**`static/admin/appointments.html`**

```html

    Citas · MediCitas

        /* Estilos específicos de esta pantalla. */
        .filter-grid {
            display: grid;
            grid-template-columns: 1fr 1fr 1.6fr 1fr 1fr;
            gap: 12px;
            align-items: start;
            margin-bottom: 12px;
        }
        .filter-grid .form-group { margin-bottom: 0; }
        .patient-picker { position: relative; }
        .patient-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            margin-top: 4px;
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            max-height: 240px;
            overflow-y: auto;
            z-index: 20;
        }
        .patient-result {
            padding: 8px 12px;
            cursor: pointer;
            border-bottom: 1px solid var(--color-border);
        }
        .patient-result:last-child { border-bottom: none; }
        .patient-result:hover { background: #f0f4f8; }
        .patient-result small { color: var(--color-muted); margin-left: 8px; }
        .patient-result.empty { color: var(--color-muted); cursor: default; }
        .patient-result.empty:hover { background: transparent; }
        .patient-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            background: #dbeafe;
            color: #1e40af;
            border-radius: var(--radius);
            font-size: 0.9rem;
        }
        .patient-chip button {
            border: none;
            background: transparent;
            cursor: pointer;
            color: inherit;
            font-size: 1.1rem;
            padding: 0;
            line-height: 1;
        }
        .row-actions { display: flex; flex-wrap: wrap; gap: 4px; }
        .row-actions .btn { white-space: nowrap; }

            Citas

                    Especialidad

                        Todas

                    Médico

                        Todos

                    Paciente

                        ×

                    Fecha

                    Estado

                        Todos
                        Agendada
                        Atendida
                        No asistió
                        Cancelada

            Limpiar filtros

        No hay citas con esos filtros.

                        Fecha
                        Hora
                        Paciente
                        Médico
                        Especialidad
                        Motivo
                        Estado
                        Acciones

            Observaciones de la cita

                Observaciones

                Guardar
                Cancelar

```
**`static/js/appointments.js`**

```js
import { apiGet, apiPatch, escapeHtml, formatName } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const STATUS_LABELS = {
    SCHEDULED: "Agendada",
    CANCELLED: "Cancelada",
    ATTENDED: "Atendida",
    NO_SHOW: "No asistió",
};

const state = {
    specialties: [],
    doctors: [],
    patientResults: [],
    selectedPatientId: null,
    appointments: [],
    editingNotesFor: null,
    searchTimer: null,
};

// Filtros
const filterSpecialty = document.getElementById("filter-specialty");
const filterDoctor = document.getElementById("filter-doctor");
const filterPatientSearch = document.getElementById("filter-patient-search");
const filterPatientResults = document.getElementById("filter-patient-results");
const filterPatientChip = document.getElementById("filter-patient-chip");
const filterPatientChipLabel = document.getElementById("filter-patient-chip-label");
const filterPatientClear = document.getElementById("filter-patient-clear");
const patientPicker = document.getElementById("patient-picker");
const filterDate = document.getElementById("filter-date");
const filterStatus = document.getElementById("filter-status");
const clearFiltersBtn = document.getElementById("clear-filters");

// Tabla y mensajes
const tbody = document.getElementById("appointments-tbody");
const tableWrap = document.getElementById("table-wrap");
const emptyMessage = document.getElementById("empty-message");
const pageError = document.getElementById("page-error");

// Modal de observaciones
const notesModal = document.getElementById("notes-modal");
const notesTextarea = document.getElementById("notes-textarea");
const notesError = document.getElementById("notes-error");
const notesSave = document.getElementById("notes-save");
const notesCancel = document.getElementById("notes-cancel");

// --- Helpers ---
function showPageError(msg) { pageError.textContent = msg; pageError.hidden = false; }
function clearPageError() { pageError.hidden = true; }

function fmtDate(iso) {
    if (!iso) return "";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
}
function fmtTime(t) { return (t || "").slice(0, 5); }

function startsAt(a) {
    return new Date(`${a.date}T${fmtTime(a.start_time)}:00`);
}
function hasStarted(a) {
    return new Date() >= startsAt(a);
}

// --- Carga inicial ---
async function loadSpecialties() {
    try {
        state.specialties = await apiGet("/api/specialties");
        filterSpecialty.innerHTML =
            'Todas' +
            state.specialties
                .map((s) => `${escapeHtml(s.name)}`)
                .join("");
    } catch (err) {
        showPageError(err.message);
    }
}

async function loadDoctors() {
    try {
        state.doctors = await apiGet("/api/doctors");
        renderDoctorOptions();
    } catch (err) {
        showPageError(err.message);
    }
}

function renderDoctorOptions() {
    const specId = filterSpecialty.value;
    const filtered = specId
        ? state.doctors.filter((d) => String(d.specialty_id) === specId)
        : state.doctors;
    const previous = filterDoctor.value;
    filterDoctor.innerHTML =
        'Todos' +
        filtered
            .map((d) => `${escapeHtml(formatName(d.first_name, d.last_name))}`)
            .join("");
    if (previous && filtered.some((d) => String(d.id) === previous)) {
        filterDoctor.value = previous;
    }
}

async function loadAppointments() {
    clearPageError();
    const params = new URLSearchParams();
    if (filterSpecialty.value) params.set("specialty_id", filterSpecialty.value);
    if (filterDoctor.value) params.set("doctor_id", filterDoctor.value);
    if (state.selectedPatientId) params.set("patient_id", state.selectedPatientId);
    if (filterDate.value) params.set("date", filterDate.value);
    if (filterStatus.value) params.set("status", filterStatus.value);
    const q = params.toString();
    try {
        state.appointments = await apiGet(`/api/appointments${q ? "?" + q : ""}`);
        renderTable();
    } catch (err) {
        showPageError(err.message);
    }
}

// --- Tabla ---
function renderTable() {
    if (state.appointments.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = state.appointments.map((a) => {
        const statusBadge = `${STATUS_LABELS[a.status] || a.status}`;
        return `

                ${fmtDate(a.date)}
                ${fmtTime(a.start_time)} – ${fmtTime(a.end_time)}
                ${escapeHtml(formatName(a.patient_first_name, a.patient_last_name))}
                ${escapeHtml(formatName(a.doctor_first_name, a.doctor_last_name))}
                ${escapeHtml(a.specialty_name)}
                ${escapeHtml(a.reason)}
                ${statusBadge}
                ${renderActions(a)}

        `;
    }).join("");

    tbody.querySelectorAll("[data-action]").forEach((btn) => {
        btn.addEventListener("click", () =>
            handleAction(btn.dataset.action, Number(btn.dataset.id))
        );
    });
}

function renderActions(a) {
    const buttons = [];
    if (a.status === "SCHEDULED") {
        const started = hasStarted(a);
        const disabledAttr = started
            ? ""
            : ' disabled title="Disponible cuando llegue la hora de inicio"';
        buttons.push(`Atendida`);
        buttons.push(`No asistió`);
        buttons.push(`Cancelar`);
    }
    buttons.push(`Observaciones`);
    return buttons.join("");
}

async function handleAction(action, id) {
    if (action === "cancel") {
        if (!confirm("¿Confirmar la cancelación de esta cita?")) return;
        await updateStatus(id, "CANCELLED");
    } else if (action === "attended") {
        await updateStatus(id, "ATTENDED");
    } else if (action === "no_show") {
        await updateStatus(id, "NO_SHOW");
    } else if (action === "notes") {
        const appointment = state.appointments.find((x) => x.id === id);
        if (appointment) openNotesModal(appointment);
    }
}

async function updateStatus(id, status) {
    clearPageError();
    try {
        await apiPatch(`/api/appointments/${id}`, { status });
        await loadAppointments();
    } catch (err) {
        showPageError(err.message);
    }
}

// --- Modal de observaciones ---
function openNotesModal(a) {
    state.editingNotesFor = a;
    notesTextarea.value = a.notes || "";
    notesError.hidden = true;
    notesModal.hidden = false;
    notesTextarea.focus();
}
function closeNotesModal() {
    state.editingNotesFor = null;
    notesModal.hidden = true;
}
async function saveNotes() {
    const a = state.editingNotesFor;
    if (!a) return;
    const text = notesTextarea.value.trim();
    notesSave.disabled = true;
    notesError.hidden = true;
    try {
        await apiPatch(`/api/appointments/${a.id}`, { notes: text || null });
        closeNotesModal();
        await loadAppointments();
    } catch (err) {
        notesError.textContent = err.message;
        notesError.hidden = false;
    } finally {
        notesSave.disabled = false;
    }
}

// --- Filtro de paciente con buscador ---
function renderPatientResults(patients) {
    state.patientResults = patients;
    if (patients.length === 0) {
        filterPatientResults.innerHTML = 'Sin coincidencias.';
    } else {
        filterPatientResults.innerHTML = patients.slice(0, 15).map((p) => `

                ${escapeHtml(formatName(p.first_name, p.last_name))}
                ${escapeHtml(p.national_id)}

        `).join("");
        filterPatientResults.querySelectorAll("[data-patient-id]").forEach((el) => {
            el.addEventListener("click", () => selectPatient(Number(el.dataset.patientId)));
        });
    }
    filterPatientResults.hidden = false;
}

function selectPatient(id) {
    const p = state.patientResults.find((x) => x.id === id);
    if (!p) return;
    state.selectedPatientId = id;
    filterPatientChipLabel.textContent = formatName(p.first_name, p.last_name);
    filterPatientChip.hidden = false;
    patientPicker.hidden = true;
    filterPatientResults.hidden = true;
    filterPatientSearch.value = "";
    loadAppointments();
}

function clearPatientFilter() {
    state.selectedPatientId = null;
    filterPatientChip.hidden = true;
    patientPicker.hidden = false;
    filterPatientResults.hidden = true;
    loadAppointments();
}

filterPatientSearch.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    const q = filterPatientSearch.value.trim();
    if (!q) {
        filterPatientResults.hidden = true;
        return;
    }
    state.searchTimer = setTimeout(async () => {
        try {
            const results = await apiGet(`/api/patients?search=${encodeURIComponent(q)}`);
            renderPatientResults(results);
        } catch {
            // Silencioso: el usuario sigue escribiendo.
        }
    }, 250);
});

document.addEventListener("click", (e) => {
    if (
        !filterPatientResults.hidden &&
        !filterPatientResults.contains(e.target) &&
        e.target !== filterPatientSearch
    ) {
        filterPatientResults.hidden = true;
    }
});

filterPatientClear.addEventListener("click", clearPatientFilter);

// --- Otros filtros ---
filterSpecialty.addEventListener("change", () => {
    renderDoctorOptions();
    loadAppointments();
});
filterDoctor.addEventListener("change", loadAppointments);
filterDate.addEventListener("change", loadAppointments);
filterStatus.addEventListener("change", loadAppointments);

clearFiltersBtn.addEventListener("click", () => {
    filterSpecialty.value = "";
    filterDoctor.value = "";
    filterDate.value = "";
    filterStatus.value = "";
    state.selectedPatientId = null;
    filterPatientChip.hidden = true;
    patientPicker.hidden = false;
    filterPatientSearch.value = "";
    filterPatientResults.hidden = true;
    renderDoctorOptions();
    loadAppointments();
});

// --- Modal handlers ---
notesSave.addEventListener("click", saveNotes);
notesCancel.addEventListener("click", closeNotesModal);
notesModal.addEventListener("click", (e) => {
    if (e.target === notesModal) closeNotesModal();
});

// --- Inicio ---
(async () => {
    await loadSpecialties();
    await loadDoctors();
    await loadAppointments();
})();
```
**Decisiones:**

- **Filtros**: se combinan con AND en el backend. Al cambiar especialidad se refresca el desplegable de médicos (solo de esa especialidad) y se conserva el médico actual si sigue siendo válido. El filtro de paciente reutiliza el buscador de RF-05 con debounce de 250 ms; al seleccionar se muestra un chip con "×" para quitarlo. "Limpiar filtros" reinicia los cinco.

- **Acciones por fila**: solo `SCHEDULED` ofrece "Atendida", "No asistió" y "Cancelar"; los finales muestran solo "Observaciones". Los dos primeros quedan deshabilitados (`disabled` + tooltip) hasta que `now >= start_time` en hora local del navegador; el backend valida lo mismo y devuelve 400 si se saltara la regla. "Cancelar" pide confirmación con `confirm()`.

- **Modal de observaciones**: editable en cualquier estado (incluidos los finales); envía `{ notes: <texto> | null }` y el backend no permite vaciar campos (PATCH sin campos → 422). Si el usuario limpia el texto, se manda `null` para borrar las observaciones existentes.

- **Estilos específicos** (grid de filtros, picker de paciente, chip, acciones) van en un `<style>` dentro de la página; el resto usa `styles.css`. Si prefieres moverlos a la hoja común, dímelo y los muevo en otra entrega.

---

### Usuario

La pantalla de citas funciona: los filtros, el buscador de paciente, los botones desactivados en citas futuras, los cambios de estado, la confirmación al cancelar y las observaciones. Ahora genera admin/new-appointment.html y js/new-appointment.js.

---

### DeepSeek AI

**`static/admin/new-appointment.html`**

```html

    Nueva cita · MediCitas

        .section {
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            padding: 20px;
            margin-bottom: 16px;
        }
        .section h2 { margin-top: 0; margin-bottom: 12px; font-size: 1.1rem; }
        .section h3 { margin: 0 0 8px; font-size: 0.9rem; color: var(--color-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }

        .patient-picker { position: relative; }
        .patient-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            margin-top: 4px;
            background: var(--color-surface);
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            max-height: 240px;
            overflow-y: auto;
            z-index: 20;
        }
        .patient-result { padding: 8px 12px; cursor: pointer; border-bottom: 1px solid var(--color-border); }
        .patient-result:last-child { border-bottom: none; }
        .patient-result:hover { background: #f0f4f8; }
        .patient-result small { color: var(--color-muted); margin-left: 8px; }
        .patient-result.empty { color: var(--color-muted); cursor: default; }
        .patient-result.empty:hover { background: transparent; }

        .patient-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            background: #dbeafe;
            color: #1e40af;
            border-radius: var(--radius);
            font-size: 0.9rem;
        }
        .patient-chip button {
            border: none;
            background: transparent;
            cursor: pointer;
            color: inherit;
            font-size: 1.1rem;
            padding: 0;
            line-height: 1;
        }

        .slot-grid { display: flex; flex-wrap: wrap; gap: 8px; }
        .slot {
            min-width: 110px;
            padding: 8px 12px;
            border: 1px solid var(--color-border);
            border-radius: var(--radius);
            background: var(--color-surface);
            font: inherit;
            cursor: pointer;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        .slot:hover:not(:disabled) { border-color: var(--color-primary); }
        .slot.selected { background: var(--color-primary); color: #ffffff; border-color: var(--color-primary); }
        .slot:disabled { cursor: not-allowed; }
        .slot.is-occupied { background: #f3f4f6; color: var(--color-muted); }
        .slot.is-past { background: #f3f4f6; color: #9ca3af; text-decoration: line-through; }
        .slot-time { font-weight: 600; font-size: 0.95rem; }
        .slot-meta { font-size: 0.75rem; }

            Nueva cita

                Datos de la cita

                        Paciente *

                            ×

                        Médico *

                            — Seleccione —

                        Fecha *

                Turno *

                    Seleccione un médico y una fecha para ver los turnos disponibles.

                            Mañana

                            Tarde (después del almuerzo)

                Motivo

                    Motivo de la cita *

                Registrar cita

```
**`static/js/new-appointment.js`**

```js
import { apiGet, apiPost, escapeHtml, formatName } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const STATUS_LABELS = {
    SCHEDULED: "Ocupado",
    CANCELLED: "Cancelada",
    ATTENDED: "Atendida",
    NO_SHOW: "No asistió",
};

const state = {
    doctors: [],
    patientResults: [],
    selectedPatient: null,
    selectedDoctorId: null,
    selectedDate: null,
    selectedSlot: null,
    slots: [],
    searchTimer: null,
};

const form = document.getElementById("appointment-form");
const patientSearch = document.getElementById("patient-search");
const patientResults = document.getElementById("patient-results");
const patientPicker = document.getElementById("patient-picker");
const patientChip = document.getElementById("patient-chip");
const patientChipLabel = document.getElementById("patient-chip-label");
const patientChipClear = document.getElementById("patient-chip-clear");
const doctorSelect = document.getElementById("doctor-select");
const dateInput = document.getElementById("date-input");
const slotsPlaceholder = document.getElementById("slots-placeholder");
const slotsSection = document.getElementById("slots-section");
const slotsEmpty = document.getElementById("slots-empty");
const slotGridMorning = document.getElementById("slot-grid-morning");
const slotGridAfternoon = document.getElementById("slot-grid-afternoon");
const reasonInput = document.getElementById("reason");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");

function setFieldError(field, message) {
    const el = document.getElementById(`${field}-error`);
    if (!el) return;
    el.textContent = message || "";
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (group) group.classList.toggle("has-error", Boolean(message));
}

function clearAllErrors() {
    ["patient", "doctor", "date", "reason"].forEach((f) => setFieldError(f, ""));
    document.getElementById("slot-error").textContent = "";
    formError.hidden = true;
}

function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtDate(iso) {
    if (!iso) return "";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
}

function isSunday(iso) {
    return new Date(`${iso}T00:00:00`).getDay() === 0;
}

// --- Datos iniciales ---
async function loadDoctors() {
    try {
        state.doctors = await apiGet("/api/doctors?is_active=true");
        doctorSelect.innerHTML =
            '— Seleccione —' +
            state.doctors
                .map(
                    (d) =>
                        `${escapeHtml(
                            formatName(d.first_name, d.last_name)
                        )} — ${escapeHtml(d.specialty_name)}`
                )
                .join("");
    } catch (err) {
        formError.textContent = err.message || "No se pudieron cargar los médicos.";
        formError.hidden = false;
    }
}

// --- Paciente ---
function renderPatientResults(patients) {
    state.patientResults = patients;
    if (patients.length === 0) {
        patientResults.innerHTML = 'Sin coincidencias.';
    } else {
        patientResults.innerHTML = patients
            .slice(0, 15)
            .map(
                (p) => `

                    ${escapeHtml(formatName(p.first_name, p.last_name))}
                    ${escapeHtml(p.national_id)}
                `
            )
            .join("");
        patientResults.querySelectorAll("[data-patient-id]").forEach((el) => {
            el.addEventListener("click", () => selectPatient(Number(el.dataset.patientId)));
        });
    }
    patientResults.hidden = false;
}

async function performPatientSearch() {
    const q = patientSearch.value.trim();
    if (!q) {
        patientResults.hidden = true;
        return;
    }
    try {
        const results = await apiGet(
            `/api/patients?search=${encodeURIComponent(q)}&is_active=true`
        );
        renderPatientResults(results);
    } catch {
        // Silencioso mientras el usuario escribe.
    }
}

function selectPatient(id) {
    const p = state.patientResults.find((x) => x.id === id);
    if (!p) return;
    state.selectedPatient = p;
    patientChipLabel.textContent = formatName(p.first_name, p.last_name);
    patientChip.hidden = false;
    patientPicker.hidden = true;
    patientResults.hidden = true;
    patientSearch.value = "";
    setFieldError("patient", "");
}

function clearPatientSelection() {
    state.selectedPatient = null;
    patientChip.hidden = true;
    patientPicker.hidden = false;
    patientSearch.focus();
}

patientSearch.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(performPatientSearch, 250);
});
patientSearch.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        performPatientSearch();
    }
});
patientChipClear.addEventListener("click", clearPatientSelection);

document.addEventListener("click", (e) => {
    if (
        !patientResults.hidden &&
        !patientResults.contains(e.target) &&
        e.target !== patientSearch
    ) {
        patientResults.hidden = true;
    }
});

// --- Turnos ---
function renderSlots() {
    if (!state.selectedDoctorId || !state.selectedDate) {
        slotsPlaceholder.hidden = false;
        slotsSection.hidden = true;
        return;
    }
    slotsPlaceholder.hidden = true;
    slotsSection.hidden = false;

    if (state.slots.length === 0) {
        slotsEmpty.textContent = isSunday(state.selectedDate)
            ? "El centro médico no atiende los domingos. Elija otra fecha."
            : "No hay turnos disponibles para esa fecha.";
        slotsEmpty.hidden = false;
        slotGridMorning.innerHTML = "";
        slotGridAfternoon.innerHTML = "";
        return;
    }
    slotsEmpty.hidden = true;

    const morning = state.slots.filter((s) => s.start_time  s.start_time >= "13:00:00");

    slotGridMorning.innerHTML = morning.map(renderSlotButton).join("");
    slotGridAfternoon.innerHTML = afternoon.map(renderSlotButton).join("");

    document.querySelectorAll(".slot[data-time]").forEach((btn) => {
        btn.addEventListener("click", () => selectSlot(btn.dataset.time));
    });
}

function renderSlotButton(slot) {
    const time = slot.start_time.slice(0, 5);
    const isSelected = state.selectedSlot === slot.start_time;
    let cls = "slot";
    let label = "";
    let disabled = false;

    if (isSelected) {
        cls += " selected";
        label = "Seleccionado";
    } else if (slot.available) {
        label = "Libre";
    } else if (slot.appointment_id) {
        cls += " is-occupied";
        label = STATUS_LABELS[slot.status] || "Ocupado";
        disabled = true;
    } else {
        cls += " is-past";
        label = "No disponible";
        disabled = true;
    }

    return `

            ${time}
            ${escapeHtml(label)}
        `;
}

function selectSlot(time) {
    state.selectedSlot = time;
    document.getElementById("slot-error").textContent = "";
    renderSlots();
}

async function refreshSlots() {
    state.selectedSlot = null;
    state.slots = [];
    renderSlots();

    if (!state.selectedDoctorId || !state.selectedDate) return;
    if (state.selectedDate  {
    state.selectedDoctorId = doctorSelect.value ? Number(doctorSelect.value) : null;
    setFieldError("doctor", "");
    refreshSlots();
});

dateInput.addEventListener("change", () => {
    state.selectedDate = dateInput.value || null;
    setFieldError("date", "");
    refreshSlots();
});

// --- Submit ---
function validate() {
    clearAllErrors();
    let ok = true;

    if (!state.selectedPatient) {
        setFieldError("patient", "Seleccione un paciente.");
        ok = false;
    }
    if (!state.selectedDoctorId) {
        setFieldError("doctor", "Seleccione un médico.");
        ok = false;
    }
    if (!state.selectedDate) {
        setFieldError("date", "Seleccione una fecha.");
        ok = false;
    } else if (state.selectedDate  500) {
        setFieldError("reason", "El motivo no puede exceder 500 caracteres.");
        ok = false;
    }

    return ok;
}

function showSuccess(appointment) {
    const patientName = formatName(appointment.patient_first_name, appointment.patient_last_name);
    const doctorName = formatName(appointment.doctor_first_name, appointment.doctor_last_name);
    const time = appointment.start_time.slice(0, 5);
    formSuccess.innerHTML = `
        Cita registrada: **${escapeHtml(patientName)}** con
        **${escapeHtml(doctorName)}** el ${fmtDate(appointment.date)} a las ${time}.
    `;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function resetForm() {
    state.selectedPatient = null;
    state.selectedDoctorId = null;
    state.selectedDate = null;
    state.selectedSlot = null;
    state.slots = [];
    patientSearch.value = "";
    patientResults.hidden = true;
    patientChip.hidden = true;
    patientPicker.hidden = false;
    doctorSelect.value = "";
    dateInput.value = "";
    reasonInput.value = "";
    renderSlots();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formSuccess.hidden = true;

    if (!validate()) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Registrando...";

    try {
        const appointment = await apiPost("/api/appointments", {
            patient_id: state.selectedPatient.id,
            doctor_id: state.selectedDoctorId,
            date: state.selectedDate,
            start_time: state.selectedSlot,
            reason: reasonInput.value.trim(),
        });
        showSuccess(appointment);
        resetForm();
    } catch (err) {
        formError.textContent = err.message || "No se pudo registrar la cita.";
        formError.hidden = false;
        // El turno pudo haber quedado ocupado; refresca la grilla.
        refreshSlots();
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Registrar cita";
    }
});

// --- Inicio ---
(async () => {
    await loadDoctors();
    dateInput.min = todayIso();
})();
```
**Decisiones:**

- El flujo sigue el orden del diseño: paciente (buscador de RF-05 restringido a activos) → médico (solo activos) → fecha → turno → motivo. Los turnos se recargan al cambiar médico o fecha; el slot seleccionado se limpia.

- La grilla muestra los 16 turnos divididos en mañana/tarde (el almuerzo queda implícito). Cada slot indica su estado: `Libre`, `Seleccionado`, el estado de la cita (`Ocupado`, `Atendida`, ...) o `No disponible` (tachado). Los no disponibles están `disabled`.

- Domingo → mensaje "El centro médico no atiende los domingos"; fecha pasada → mensaje específico y no se llama a la API; `dateInput.min` como ayuda visual. El backend vuelve a validar todo.

- Tras crear: mensaje de éxito con paciente/médico/fecha/hora y reset completo del formulario (el admin puede registrar otra de inmediato). Si el POST falla, se refresca la grilla por si el turno se ocupó entre medias; la validación por campo usa `.field-error` junto a cada control.

---

### Usuario

Nueva cita funciona: la validación de campos, el buscador solo con pacientes activos, la grilla de turnos con sus estados, el domingo, el registro con el resumen y el conflicto de paciente muestra el error del backend. Ahora genera index.html y js/index.js para la agenda pública.

---

### DeepSeek AI

Antes de generarlo, hay un punto del diseño que no cierra y prefiero no asumir.

**Problema:** RF-10 pide filtrar la agenda pública por médico, pero `GET /api/doctors` requiere token de admin (sección 9) y la agenda pública no tiene login. Sin una fuente pública de médicos, no hay forma limpia de poblar el desplegable.

**Opciones:**

- **(a)** Construir el desplegable a partir de los médicos que aparecen en las citas del día visible. Sin cambio de backend. Limitación: un médico sin citas ese día no aparece en el filtro (y en un domingo el desplegable queda vacío).

- **(b)** Agregar un endpoint público `GET /api/public-doctors` (red interna, sin auth) que devuelva `id`, nombres, apellidos y especialidad de los médicos activos. Implica ampliar la sección 9 del diseño.

- **(c)** Reemplazar el desplegable por un campo de texto que filtre en cliente por nombre del médico, sobre las citas del día.

Recomiendo **(b)** porque cumple RF-10 sin parches y respeta el principio de "la agenda pública solo muestra lo necesario". Dime cuál prefieres y lo genero de inmediato.

---

### Usuario

Prefiero la opción (a): el filtro sirve para que cada médico encuentre sus citas, y si un médico no tiene citas ese día, igual vería la agenda vacía. Así no hace falta tocar el backend. Si el día no tiene citas, que se muestre un mensaje claro en vez del desplegable vacío.

---

### DeepSeek AI

**`static/index.html`**

```html

    Agenda · MediCitas

                Agenda médica
                Uso interno del centro médico

            Acceso administrador

                    Fecha

                    Médico

                        Todos

                        Hora
                        Médico
                        Especialidad
                        Paciente

```
**`static/js/index.js`**

```js
import { apiGet, escapeHtml, formatName } from "./api.js";

const dateInput = document.getElementById("date-input");
const doctorSelect = document.getElementById("doctor-select");
const doctorFilterGroup = document.getElementById("doctor-filter-group");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("schedule-tbody");
const emptyMsg = document.getElementById("empty-msg");
const errorMsg = document.getElementById("error-msg");

let appointments = [];

function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function fmtTime(t) {
    return (t || "").slice(0, 5);
}

function clearMessages() {
    errorMsg.hidden = true;
    emptyMsg.hidden = true;
}

function showError(message) {
    tableWrap.hidden = true;
    errorMsg.textContent = message;
    errorMsg.hidden = false;
}

function showEmpty(message) {
    tableWrap.hidden = true;
    emptyMsg.textContent = message;
    emptyMsg.hidden = false;
}

function doctorKey(a) {
    return `${a.doctor_first_name}|${a.doctor_last_name}`;
}

function renderDoctorOptions() {
    if (appointments.length === 0) {
        doctorFilterGroup.hidden = true;
        doctorSelect.innerHTML = 'Todos';
        return;
    }
    doctorFilterGroup.hidden = false;

    const seen = new Map();
    for (const a of appointments) {
        const key = doctorKey(a);
        if (!seen.has(key)) {
            seen.set(key, formatName(a.doctor_first_name, a.doctor_last_name));
        }
    }
    const options = [...seen.entries()]
        .map(([key, label]) => ({ key, label }))
        .sort((a, b) => a.label.localeCompare(b.label, "es"));

    const previous = doctorSelect.value;
    doctorSelect.innerHTML =
        'Todos' +
        options
            .map(
                (o) =>
                    `${escapeHtml(o.label)}`
            )
            .join("");

    if (previous && options.some((o) => o.key === previous)) {
        doctorSelect.value = previous;
    }
}

function renderTable() {
    const selected = doctorSelect.value;
    const filtered = selected
        ? appointments.filter((a) => doctorKey(a) === selected)
        : appointments;

    if (filtered.length === 0) {
        if (appointments.length === 0) {
            showEmpty("No hay citas registradas para esta fecha.");
        } else {
            showEmpty("No hay citas del médico seleccionado para esta fecha.");
        }
        return;
    }
    emptyMsg.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = filtered
        .map(
            (a) => `

                ${fmtTime(a.start_time)} – ${fmtTime(a.end_time)}
                ${escapeHtml(formatName(a.doctor_first_name, a.doctor_last_name))}
                ${escapeHtml(a.specialty_name)}
                ${escapeHtml(formatName(a.patient_first_name, a.patient_last_name))}
            `
        )
        .join("");
}

async function loadSchedule() {
    clearMessages();
    const dateStr = dateInput.value;
    if (!dateStr) {
        appointments = [];
        renderDoctorOptions();
        showEmpty("Seleccione una fecha para consultar la agenda.");
        return;
    }
    try {
        appointments = await apiGet(
            `/api/public-schedule?date=${encodeURIComponent(dateStr)}`
        );
    } catch (err) {
        appointments = [];
        renderDoctorOptions();
        showError(err.message || "No se pudo cargar la agenda.");
        return;
    }
    renderDoctorOptions();
    renderTable();
}

dateInput.addEventListener("change", loadSchedule);
doctorSelect.addEventListener("change", renderTable);

// --- Inicio ---
dateInput.value = todayIso();
loadSchedule();
```
**Decisiones:**

- **Filtro por médico sin tocar el backend**: el desplegable se arma a partir de las citas del día (pares únicos `doctor_first_name|doctor_last_name` del propio `PublicScheduleItemRead`), ordenado alfabéticamente por "Apellidos Nombres". Si dos médicos tuvieran exactamente el mismo nombre y apellido, el filtro los agruparía — caso irreal en este proyecto y no afecta la corrección del listado.

- **Mensajes diferenciados**: sin citas ese día → "No hay citas registradas para esta fecha" y se oculta el desplegable de médico; con citas pero ninguna del médico seleccionado → "No hay citas del médico seleccionado para esta fecha". Error 403 del backend (fuera de red interna) se muestra tal cual, con su `detail` en español.

- Solo se muestran hora de inicio/fin, médico, especialidad y paciente ("Apellidos Nombres"); ni cédula, ni teléfono, ni motivo, ni observaciones, tal como exige RF-10. No hay `initAdminPage()` ni token: la página es pública (dentro de la red interna).

- El desplegable conserva la selección si el médico sigue apareciendo al cambiar de fecha; si ya no tiene citas ese día, vuelve a "Todos" implícitamente. `loadSchedule` se dispara al cambiar la fecha; el filtro por médico se aplica en cliente sin nueva petición.

---

### Usuario

Un ajuste pequeño: en seed.py tienes tus propias copias de las funciones que calculan los turnos, pero services/slots.py ya tiene business_slots() y add_minutes() públicas. Cambia seed.py para que importe y use las de slots.py y elimina las copias. No cambies nada más de la lógica de los datos de ejemplo. Te adjunto el seed.py actual. Dame el archivo completo.

---

### DeepSeek AI

**`app/seed.py`**

```python
"""Database seeding: admin bootstrap and sample data."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import BUSINESS_DAYS, SLOT_DURATION_MINUTES, TIMEZONE, settings
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
from app.services.slots import add_minutes, business_slots

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

    slots = business_slots()
    past_slots: list[time] = []
    future_slots: list[time] = []
    if today.weekday() in BUSINESS_DAYS:
        past_slots = [s for s in slots if s  current_time]

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
                end_time=add_minutes(start, SLOT_DURATION_MINUTES),
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
```
**Decisiones:**

- `_business_slots` y `_add_minutes` locales desaparecen; ahora se importan `business_slots` y `add_minutes` de `app.services.slots`. También se elimina el import de `MORNING_START`, `MORNING_LAST_SLOT`, `AFTERNOON_START` y `AFTERNOON_LAST_SLOT`, que solo usaban esas copias.

- Se mantienen `BUSINESS_DAYS` (para `_next_business_day` y para decidir si hoy es día hábil) y `SLOT_DURATION_MINUTES` (para calcular `end_time` de cada cita del seed).

- La lógica de datos de ejemplo no cambia: mismos pares paciente-médico, mismos índices en `slots`, mismo cálculo de `past_slots`/`future_slots`. Los turnos generados son idénticos porque `business_slots()` produce exactamente la misma lista que la copia anterior.

---

### Usuario

Otro ajuste de limpieza en el frontend. Las funciones todayIso(), fmtDate() y fmtTime() están repetidas en varios archivos: todayIso en patients.js, new-appointment.js e index.js; fmtDate en new-appointment.js y appointments.js; fmtTime en appointments.js e index.js.
Muévelas a api.js como funciones exportadas, junto a escapeHtml y formatName, y haz que esos archivos las importen de ahí en lugar de tener su propia copia.
Aprovecha también para que la tabla de pacientes muestre la fecha de nacimiento como dd/mm/aaaa usando fmtDate. El input del formulario sigue igual, con type="date".
No cambies nada más. Te adjunto los archivos actuales. Dame completos todos los archivos que modifiques.

---

### DeepSeek AI

**`static/js/api.js`**

```js
// Common API client and small helpers shared by all pages.

const TOKEN_KEY = "medicitas_token";

export function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
    sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
    sessionStorage.removeItem(TOKEN_KEY);
}

async function request(method, path, body, options) {
    const opts = options || {};
    const redirectOn401 = opts.redirectOn401 !== false;

    const headers = {};
    if (body !== undefined) {
        headers["Content-Type"] = "application/json";
    }
    const token = getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let response;
    try {
        response = await fetch(path, {
            method,
            headers,
            body: body !== undefined ? JSON.stringify(body) : undefined,
        });
    } catch {
        throw new Error("No se pudo conectar con el servidor.");
    }

    if (response.status === 401 && token && redirectOn401) {
        clearToken();
        window.location.replace("/login.html");
        throw new Error("Sesión expirada.");
    }

    const text = await response.text();
    let data = null;
    if (text) {
        try { data = JSON.parse(text); } catch { data = null; }
    }

    if (!response.ok) {
        const detail = data && data.detail ? String(data.detail) : `Error ${response.status}.`;
        throw new Error(detail);
    }
    return data;
}

export function apiGet(path, options) {
    return request("GET", path, undefined, options);
}
export function apiPost(path, body, options) {
    return request("POST", path, body, options);
}
export function apiPut(path, body, options) {
    return request("PUT", path, body, options);
}
export function apiPatch(path, body, options) {
    return request("PATCH", path, body, options);
}

export function escapeHtml(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replaceAll("&", "&")
        .replaceAll("", ">")
        .replaceAll('"', """)
        .replaceAll("'", "'");
}

// "Apellidos Nombres" (sección 12).
export function formatName(firstName, lastName) {
    return [lastName, firstName]
        .filter((part) => part && String(part).trim())
        .join(" ")
        .trim();
}

export function todayIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function fmtDate(iso) {
    if (!iso) return "";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
}

export function fmtTime(t) {
    return (t || "").slice(0, 5);
}
```
**`static/js/patients.js`**

```js
import { apiGet, apiPost, apiPut, escapeHtml, formatName, fmtDate, todayIso } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const form = document.getElementById("patient-form");
const formTitle = document.getElementById("form-title");
const nationalIdInput = document.getElementById("national_id");
const birthDateInput = document.getElementById("birth_date");
const firstNameInput = document.getElementById("first_name");
const lastNameInput = document.getElementById("last_name");
const phoneInput = document.getElementById("phone");
const emailInput = document.getElementById("email");
const isActiveGroup = document.getElementById("is-active-group");
const isActiveInput = document.getElementById("is_active");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");
const submitBtn = document.getElementById("submit-btn");
const cancelBtn = document.getElementById("cancel-btn");
const emptyMessage = document.getElementById("empty-message");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("patients-tbody");
const searchInput = document.getElementById("search");
const filterActive = document.getElementById("filter-active");

let editingId = null;
let patients = [];

function setFieldError(field, message) {
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (!group) return;
    group.classList.toggle("has-error", Boolean(message));
    group.querySelector(".field-error").textContent = message || "";
}

function clearAllFieldErrors() {
    ["national_id", "birth_date", "first_name", "last_name", "phone", "email", "is_active"]
        .forEach((f) => setFieldError(f, ""));
}

function resetForm() {
    editingId = null;
    form.reset();
    clearAllFieldErrors();
    isActiveGroup.hidden = true;
    isActiveInput.checked = false;
    formTitle.textContent = "Nuevo paciente";
    submitBtn.textContent = "Crear";
    cancelBtn.hidden = true;
    formError.hidden = true;
    formSuccess.hidden = true;
}

function showError(message) {
    formError.textContent = message;
    formError.hidden = false;
    formSuccess.hidden = true;
}

function showSuccess(message) {
    formSuccess.textContent = message;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function validate() {
    clearAllFieldErrors();
    let ok = true;

    const nid = nationalIdInput.value.trim();
    if (!nid) { setFieldError("national_id", "La cédula es obligatoria."); ok = false; }
    else if (nid.length > 20) { setFieldError("national_id", "Máximo 20 caracteres."); ok = false; }

    const first = firstNameInput.value.trim();
    if (!first) { setFieldError("first_name", "Los nombres son obligatorios."); ok = false; }
    else if (first.length > 100) { setFieldError("first_name", "Máximo 100 caracteres."); ok = false; }

    const last = lastNameInput.value.trim();
    if (!last) { setFieldError("last_name", "Los apellidos son obligatorios."); ok = false; }
    else if (last.length > 100) { setFieldError("last_name", "Máximo 100 caracteres."); ok = false; }

    const phone = phoneInput.value.trim();
    if (!phone) { setFieldError("phone", "El teléfono es obligatorio."); ok = false; }
    else if (phone.length > 20) { setFieldError("phone", "Máximo 20 caracteres."); ok = false; }

    const email = emailInput.value.trim();
    if (email.length > 150) { setFieldError("email", "Máximo 150 caracteres."); ok = false; }
    else if (email && !EMAIL_RE.test(email)) { setFieldError("email", "Formato de email inválido."); ok = false; }

    const birth = birthDateInput.value;
    if (birth && birth > todayIso()) {
        setFieldError("birth_date", "La fecha de nacimiento no puede ser futura.");
        ok = false;
    }

    return ok;
}

function renderTable() {
    if (patients.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = patients
        .map((p) => {
            const stateBadge = p.is_active
                ? 'Activo'
                : 'Inactivo';
            return `

                ${escapeHtml(p.national_id)}
                ${escapeHtml(formatName(p.first_name, p.last_name))}
                ${escapeHtml(fmtDate(p.birth_date))}
                ${escapeHtml(p.phone)}
                ${escapeHtml(p.email || "")}
                ${stateBadge}

                    Editar

            `;
        })
        .join("");

    tbody.querySelectorAll("[data-edit-id]").forEach((btn) => {
        btn.addEventListener("click", () => startEdit(Number(btn.dataset.editId)));
    });
}

function startEdit(id) {
    const patient = patients.find((p) => p.id === id);
    if (!patient) return;
    editingId = id;
    nationalIdInput.value = patient.national_id;
    birthDateInput.value = patient.birth_date || "";
    firstNameInput.value = patient.first_name;
    lastNameInput.value = patient.last_name;
    phoneInput.value = patient.phone;
    emailInput.value = patient.email || "";
    isActiveInput.checked = patient.is_active;
    isActiveGroup.hidden = false;
    clearAllFieldErrors();
    formError.hidden = true;
    formSuccess.hidden = true;
    formTitle.textContent = `Editar paciente #${id}`;
    submitBtn.textContent = "Guardar";
    cancelBtn.hidden = false;
    nationalIdInput.focus();
}

async function loadPatients() {
    const params = new URLSearchParams();
    const search = searchInput.value.trim();
    if (search) params.set("search", search);
    if (filterActive.value) params.set("is_active", filterActive.value);
    const query = params.toString();
    try {
        patients = await apiGet(`/api/patients${query ? "?" + query : ""}`);
        renderTable();
    } catch (err) {
        showError(err.message || "No se pudieron cargar los pacientes.");
    }
}

function resetFormKeepMessage() {
    const successText = formSuccess.textContent;
    const showSuccessMsg = !formSuccess.hidden;
    resetForm();
    if (showSuccessMsg) {
        formSuccess.textContent = successText;
        formSuccess.hidden = false;
    }
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formError.hidden = true;
    formSuccess.hidden = true;

    if (!validate()) return;

    const payload = {
        national_id: nationalIdInput.value.trim(),
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        birth_date: birthDateInput.value || null,
        phone: phoneInput.value.trim(),
        email: emailInput.value.trim() || null,
    };

    submitBtn.disabled = true;
    try {
        if (editingId === null) {
            await apiPost("/api/patients", payload);
            showSuccess("Paciente creado.");
        } else {
            payload.is_active = isActiveInput.checked;
            await apiPut(`/api/patients/${editingId}`, payload);
            showSuccess("Paciente actualizado.");
        }
        resetFormKeepMessage();
        await loadPatients();
    } catch (err) {
        showError(err.message || "No se pudo guardar el paciente.");
    } finally {
        submitBtn.disabled = false;
    }
});

cancelBtn.addEventListener("click", () => resetForm());

let searchTimer = null;
searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadPatients, 250);
});
filterActive.addEventListener("change", loadPatients);

loadPatients();
```
**`static/js/appointments.js`**

```js
import { apiGet, apiPatch, escapeHtml, formatName, fmtDate, fmtTime } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const STATUS_LABELS = {
    SCHEDULED: "Agendada",
    CANCELLED: "Cancelada",
    ATTENDED: "Atendida",
    NO_SHOW: "No asistió",
};

const state = {
    specialties: [],
    doctors: [],
    patientResults: [],
    selectedPatientId: null,
    appointments: [],
    editingNotesFor: null,
    searchTimer: null,
};

// Filtros
const filterSpecialty = document.getElementById("filter-specialty");
const filterDoctor = document.getElementById("filter-doctor");
const filterPatientSearch = document.getElementById("filter-patient-search");
const filterPatientResults = document.getElementById("filter-patient-results");
const filterPatientChip = document.getElementById("filter-patient-chip");
const filterPatientChipLabel = document.getElementById("filter-patient-chip-label");
const filterPatientClear = document.getElementById("filter-patient-clear");
const patientPicker = document.getElementById("patient-picker");
const filterDate = document.getElementById("filter-date");
const filterStatus = document.getElementById("filter-status");
const clearFiltersBtn = document.getElementById("clear-filters");

// Tabla y mensajes
const tbody = document.getElementById("appointments-tbody");
const tableWrap = document.getElementById("table-wrap");
const emptyMessage = document.getElementById("empty-message");
const pageError = document.getElementById("page-error");

// Modal de observaciones
const notesModal = document.getElementById("notes-modal");
const notesTextarea = document.getElementById("notes-textarea");
const notesError = document.getElementById("notes-error");
const notesSave = document.getElementById("notes-save");
const notesCancel = document.getElementById("notes-cancel");

// --- Helpers ---
function showPageError(msg) { pageError.textContent = msg; pageError.hidden = false; }
function clearPageError() { pageError.hidden = true; }

function startsAt(a) {
    return new Date(`${a.date}T${fmtTime(a.start_time)}:00`);
}
function hasStarted(a) {
    return new Date() >= startsAt(a);
}

// --- Carga inicial ---
async function loadSpecialties() {
    try {
        state.specialties = await apiGet("/api/specialties");
        filterSpecialty.innerHTML =
            'Todas' +
            state.specialties
                .map((s) => `${escapeHtml(s.name)}`)
                .join("");
    } catch (err) {
        showPageError(err.message);
    }
}

async function loadDoctors() {
    try {
        state.doctors = await apiGet("/api/doctors");
        renderDoctorOptions();
    } catch (err) {
        showPageError(err.message);
    }
}

function renderDoctorOptions() {
    const specId = filterSpecialty.value;
    const filtered = specId
        ? state.doctors.filter((d) => String(d.specialty_id) === specId)
        : state.doctors;
    const previous = filterDoctor.value;
    filterDoctor.innerHTML =
        'Todos' +
        filtered
            .map((d) => `${escapeHtml(formatName(d.first_name, d.last_name))}`)
            .join("");
    if (previous && filtered.some((d) => String(d.id) === previous)) {
        filterDoctor.value = previous;
    }
}

async function loadAppointments() {
    clearPageError();
    const params = new URLSearchParams();
    if (filterSpecialty.value) params.set("specialty_id", filterSpecialty.value);
    if (filterDoctor.value) params.set("doctor_id", filterDoctor.value);
    if (state.selectedPatientId) params.set("patient_id", state.selectedPatientId);
    if (filterDate.value) params.set("date", filterDate.value);
    if (filterStatus.value) params.set("status", filterStatus.value);
    const q = params.toString();
    try {
        state.appointments = await apiGet(`/api/appointments${q ? "?" + q : ""}`);
        renderTable();
    } catch (err) {
        showPageError(err.message);
    }
}

// --- Tabla ---
function renderTable() {
    if (state.appointments.length === 0) {
        emptyMessage.hidden = false;
        tableWrap.hidden = true;
        return;
    }
    emptyMessage.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = state.appointments.map((a) => {
        const statusBadge = `${STATUS_LABELS[a.status] || a.status}`;
        return `

                ${fmtDate(a.date)}
                ${fmtTime(a.start_time)} – ${fmtTime(a.end_time)}
                ${escapeHtml(formatName(a.patient_first_name, a.patient_last_name))}
                ${escapeHtml(formatName(a.doctor_first_name, a.doctor_last_name))}
                ${escapeHtml(a.specialty_name)}
                ${escapeHtml(a.reason)}
                ${statusBadge}
                ${renderActions(a)}

        `;
    }).join("");

    tbody.querySelectorAll("[data-action]").forEach((btn) => {
        btn.addEventListener("click", () =>
            handleAction(btn.dataset.action, Number(btn.dataset.id))
        );
    });
}

function renderActions(a) {
    const buttons = [];
    if (a.status === "SCHEDULED") {
        const started = hasStarted(a);
        const disabledAttr = started
            ? ""
            : ' disabled title="Disponible cuando llegue la hora de inicio"';
        buttons.push(`Atendida`);
        buttons.push(`No asistió`);
        buttons.push(`Cancelar`);
    }
    buttons.push(`Observaciones`);
    return buttons.join("");
}

async function handleAction(action, id) {
    if (action === "cancel") {
        if (!confirm("¿Confirmar la cancelación de esta cita?")) return;
        await updateStatus(id, "CANCELLED");
    } else if (action === "attended") {
        await updateStatus(id, "ATTENDED");
    } else if (action === "no_show") {
        await updateStatus(id, "NO_SHOW");
    } else if (action === "notes") {
        const appointment = state.appointments.find((x) => x.id === id);
        if (appointment) openNotesModal(appointment);
    }
}

async function updateStatus(id, status) {
    clearPageError();
    try {
        await apiPatch(`/api/appointments/${id}`, { status });
        await loadAppointments();
    } catch (err) {
        showPageError(err.message);
    }
}

// --- Modal de observaciones ---
function openNotesModal(a) {
    state.editingNotesFor = a;
    notesTextarea.value = a.notes || "";
    notesError.hidden = true;
    notesModal.hidden = false;
    notesTextarea.focus();
}
function closeNotesModal() {
    state.editingNotesFor = null;
    notesModal.hidden = true;
}
async function saveNotes() {
    const a = state.editingNotesFor;
    if (!a) return;
    const text = notesTextarea.value.trim();
    notesSave.disabled = true;
    notesError.hidden = true;
    try {
        await apiPatch(`/api/appointments/${a.id}`, { notes: text || null });
        closeNotesModal();
        await loadAppointments();
    } catch (err) {
        notesError.textContent = err.message;
        notesError.hidden = false;
    } finally {
        notesSave.disabled = false;
    }
}

// --- Filtro de paciente con buscador ---
function renderPatientResults(patients) {
    state.patientResults = patients;
    if (patients.length === 0) {
        filterPatientResults.innerHTML = 'Sin coincidencias.';
    } else {
        filterPatientResults.innerHTML = patients.slice(0, 15).map((p) => `

                ${escapeHtml(formatName(p.first_name, p.last_name))}
                ${escapeHtml(p.national_id)}

        `).join("");
        filterPatientResults.querySelectorAll("[data-patient-id]").forEach((el) => {
            el.addEventListener("click", () => selectPatient(Number(el.dataset.patientId)));
        });
    }
    filterPatientResults.hidden = false;
}

function selectPatient(id) {
    const p = state.patientResults.find((x) => x.id === id);
    if (!p) return;
    state.selectedPatientId = id;
    filterPatientChipLabel.textContent = formatName(p.first_name, p.last_name);
    filterPatientChip.hidden = false;
    patientPicker.hidden = true;
    filterPatientResults.hidden = true;
    filterPatientSearch.value = "";
    loadAppointments();
}

function clearPatientFilter() {
    state.selectedPatientId = null;
    filterPatientChip.hidden = true;
    patientPicker.hidden = false;
    filterPatientResults.hidden = true;
    loadAppointments();
}

filterPatientSearch.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    const q = filterPatientSearch.value.trim();
    if (!q) {
        filterPatientResults.hidden = true;
        return;
    }
    state.searchTimer = setTimeout(async () => {
        try {
            const results = await apiGet(`/api/patients?search=${encodeURIComponent(q)}`);
            renderPatientResults(results);
        } catch {
            // Silencioso: el usuario sigue escribiendo.
        }
    }, 250);
});

document.addEventListener("click", (e) => {
    if (
        !filterPatientResults.hidden &&
        !filterPatientResults.contains(e.target) &&
        e.target !== filterPatientSearch
    ) {
        filterPatientResults.hidden = true;
    }
});

filterPatientClear.addEventListener("click", clearPatientFilter);

// --- Otros filtros ---
filterSpecialty.addEventListener("change", () => {
    renderDoctorOptions();
    loadAppointments();
});
filterDoctor.addEventListener("change", loadAppointments);
filterDate.addEventListener("change", loadAppointments);
filterStatus.addEventListener("change", loadAppointments);

clearFiltersBtn.addEventListener("click", () => {
    filterSpecialty.value = "";
    filterDoctor.value = "";
    filterDate.value = "";
    filterStatus.value = "";
    state.selectedPatientId = null;
    filterPatientChip.hidden = true;
    patientPicker.hidden = false;
    filterPatientSearch.value = "";
    filterPatientResults.hidden = true;
    renderDoctorOptions();
    loadAppointments();
});

// --- Modal handlers ---
notesSave.addEventListener("click", saveNotes);
notesCancel.addEventListener("click", closeNotesModal);
notesModal.addEventListener("click", (e) => {
    if (e.target === notesModal) closeNotesModal();
});

// --- Inicio ---
(async () => {
    await loadSpecialties();
    await loadDoctors();
    await loadAppointments();
})();
```
**`static/js/new-appointment.js`**

```js
import { apiGet, apiPost, escapeHtml, formatName, fmtDate, todayIso } from "./api.js";
import { initAdminPage } from "./admin-nav.js";

if (!initAdminPage()) throw new Error("Redirecting to login");

const STATUS_LABELS = {
    SCHEDULED: "Ocupado",
    CANCELLED: "Cancelada",
    ATTENDED: "Atendida",
    NO_SHOW: "No asistió",
};

const state = {
    doctors: [],
    patientResults: [],
    selectedPatient: null,
    selectedDoctorId: null,
    selectedDate: null,
    selectedSlot: null,
    slots: [],
    searchTimer: null,
};

const form = document.getElementById("appointment-form");
const patientSearch = document.getElementById("patient-search");
const patientResults = document.getElementById("patient-results");
const patientPicker = document.getElementById("patient-picker");
const patientChip = document.getElementById("patient-chip");
const patientChipLabel = document.getElementById("patient-chip-label");
const patientChipClear = document.getElementById("patient-chip-clear");
const doctorSelect = document.getElementById("doctor-select");
const dateInput = document.getElementById("date-input");
const slotsPlaceholder = document.getElementById("slots-placeholder");
const slotsSection = document.getElementById("slots-section");
const slotsEmpty = document.getElementById("slots-empty");
const slotGridMorning = document.getElementById("slot-grid-morning");
const slotGridAfternoon = document.getElementById("slot-grid-afternoon");
const reasonInput = document.getElementById("reason");
const submitBtn = document.getElementById("submit-btn");
const formError = document.getElementById("form-error");
const formSuccess = document.getElementById("form-success");

function setFieldError(field, message) {
    const el = document.getElementById(`${field}-error`);
    if (!el) return;
    el.textContent = message || "";
    const group = form.querySelector(`.form-group[data-field="${field}"]`);
    if (group) group.classList.toggle("has-error", Boolean(message));
}

function clearAllErrors() {
    ["patient", "doctor", "date", "reason"].forEach((f) => setFieldError(f, ""));
    document.getElementById("slot-error").textContent = "";
    formError.hidden = true;
}

function isSunday(iso) {
    return new Date(`${iso}T00:00:00`).getDay() === 0;
}

// --- Datos iniciales ---
async function loadDoctors() {
    try {
        state.doctors = await apiGet("/api/doctors?is_active=true");
        doctorSelect.innerHTML =
            '— Seleccione —' +
            state.doctors
                .map(
                    (d) =>
                        `${escapeHtml(
                            formatName(d.first_name, d.last_name)
                        )} — ${escapeHtml(d.specialty_name)}`
                )
                .join("");
    } catch (err) {
        formError.textContent = err.message || "No se pudieron cargar los médicos.";
        formError.hidden = false;
    }
}

// --- Paciente ---
function renderPatientResults(patients) {
    state.patientResults = patients;
    if (patients.length === 0) {
        patientResults.innerHTML = 'Sin coincidencias.';
    } else {
        patientResults.innerHTML = patients
            .slice(0, 15)
            .map(
                (p) => `

                    ${escapeHtml(formatName(p.first_name, p.last_name))}
                    ${escapeHtml(p.national_id)}
                `
            )
            .join("");
        patientResults.querySelectorAll("[data-patient-id]").forEach((el) => {
            el.addEventListener("click", () => selectPatient(Number(el.dataset.patientId)));
        });
    }
    patientResults.hidden = false;
}

async function performPatientSearch() {
    const q = patientSearch.value.trim();
    if (!q) {
        patientResults.hidden = true;
        return;
    }
    try {
        const results = await apiGet(
            `/api/patients?search=${encodeURIComponent(q)}&is_active=true`
        );
        renderPatientResults(results);
    } catch {
        // Silencioso mientras el usuario escribe.
    }
}

function selectPatient(id) {
    const p = state.patientResults.find((x) => x.id === id);
    if (!p) return;
    state.selectedPatient = p;
    patientChipLabel.textContent = formatName(p.first_name, p.last_name);
    patientChip.hidden = false;
    patientPicker.hidden = true;
    patientResults.hidden = true;
    patientSearch.value = "";
    setFieldError("patient", "");
}

function clearPatientSelection() {
    state.selectedPatient = null;
    patientChip.hidden = true;
    patientPicker.hidden = false;
    patientSearch.focus();
}

patientSearch.addEventListener("input", () => {
    clearTimeout(state.searchTimer);
    state.searchTimer = setTimeout(performPatientSearch, 250);
});
patientSearch.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        e.preventDefault();
        performPatientSearch();
    }
});
patientChipClear.addEventListener("click", clearPatientSelection);

document.addEventListener("click", (e) => {
    if (
        !patientResults.hidden &&
        !patientResults.contains(e.target) &&
        e.target !== patientSearch
    ) {
        patientResults.hidden = true;
    }
});

// --- Turnos ---
function renderSlots() {
    if (!state.selectedDoctorId || !state.selectedDate) {
        slotsPlaceholder.hidden = false;
        slotsSection.hidden = true;
        return;
    }
    slotsPlaceholder.hidden = true;
    slotsSection.hidden = false;

    if (state.slots.length === 0) {
        slotsEmpty.textContent = isSunday(state.selectedDate)
            ? "El centro médico no atiende los domingos. Elija otra fecha."
            : "No hay turnos disponibles para esa fecha.";
        slotsEmpty.hidden = false;
        slotGridMorning.innerHTML = "";
        slotGridAfternoon.innerHTML = "";
        return;
    }
    slotsEmpty.hidden = true;

    const morning = state.slots.filter((s) => s.start_time  s.start_time >= "13:00:00");

    slotGridMorning.innerHTML = morning.map(renderSlotButton).join("");
    slotGridAfternoon.innerHTML = afternoon.map(renderSlotButton).join("");

    document.querySelectorAll(".slot[data-time]").forEach((btn) => {
        btn.addEventListener("click", () => selectSlot(btn.dataset.time));
    });
}

function renderSlotButton(slot) {
    const time = slot.start_time.slice(0, 5);
    const isSelected = state.selectedSlot === slot.start_time;
    let cls = "slot";
    let label = "";
    let disabled = false;

    if (isSelected) {
        cls += " selected";
        label = "Seleccionado";
    } else if (slot.available) {
        label = "Libre";
    } else if (slot.appointment_id) {
        cls += " is-occupied";
        label = STATUS_LABELS[slot.status] || "Ocupado";
        disabled = true;
    } else {
        cls += " is-past";
        label = "No disponible";
        disabled = true;
    }

    return `

            ${time}
            ${escapeHtml(label)}
        `;
}

function selectSlot(time) {
    state.selectedSlot = time;
    document.getElementById("slot-error").textContent = "";
    renderSlots();
}

async function refreshSlots() {
    state.selectedSlot = null;
    state.slots = [];
    renderSlots();

    if (!state.selectedDoctorId || !state.selectedDate) return;
    if (state.selectedDate  {
    state.selectedDoctorId = doctorSelect.value ? Number(doctorSelect.value) : null;
    setFieldError("doctor", "");
    refreshSlots();
});

dateInput.addEventListener("change", () => {
    state.selectedDate = dateInput.value || null;
    setFieldError("date", "");
    refreshSlots();
});

// --- Submit ---
function validate() {
    clearAllErrors();
    let ok = true;

    if (!state.selectedPatient) {
        setFieldError("patient", "Seleccione un paciente.");
        ok = false;
    }
    if (!state.selectedDoctorId) {
        setFieldError("doctor", "Seleccione un médico.");
        ok = false;
    }
    if (!state.selectedDate) {
        setFieldError("date", "Seleccione una fecha.");
        ok = false;
    } else if (state.selectedDate  500) {
        setFieldError("reason", "El motivo no puede exceder 500 caracteres.");
        ok = false;
    }

    return ok;
}

function showSuccess(appointment) {
    const patientName = formatName(appointment.patient_first_name, appointment.patient_last_name);
    const doctorName = formatName(appointment.doctor_first_name, appointment.doctor_last_name);
    const time = appointment.start_time.slice(0, 5);
    formSuccess.innerHTML = `
        Cita registrada: **${escapeHtml(patientName)}** con
        **${escapeHtml(doctorName)}** el ${fmtDate(appointment.date)} a las ${time}.
    `;
    formSuccess.hidden = false;
    formError.hidden = true;
}

function resetForm() {
    state.selectedPatient = null;
    state.selectedDoctorId = null;
    state.selectedDate = null;
    state.selectedSlot = null;
    state.slots = [];
    patientSearch.value = "";
    patientResults.hidden = true;
    patientChip.hidden = true;
    patientPicker.hidden = false;
    doctorSelect.value = "";
    dateInput.value = "";
    reasonInput.value = "";
    renderSlots();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    formSuccess.hidden = true;

    if (!validate()) return;

    submitBtn.disabled = true;
    submitBtn.textContent = "Registrando...";

    try {
        const appointment = await apiPost("/api/appointments", {
            patient_id: state.selectedPatient.id,
            doctor_id: state.selectedDoctorId,
            date: state.selectedDate,
            start_time: state.selectedSlot,
            reason: reasonInput.value.trim(),
        });
        showSuccess(appointment);
        resetForm();
    } catch (err) {
        formError.textContent = err.message || "No se pudo registrar la cita.";
        formError.hidden = false;
        // El turno pudo haber quedado ocupado; refresca la grilla.
        refreshSlots();
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = "Registrar cita";
    }
});

// --- Inicio ---
(async () => {
    await loadDoctors();
    dateInput.min = todayIso();
})();
```
**`static/js/index.js`**

```js
import { apiGet, escapeHtml, formatName, fmtTime, todayIso } from "./api.js";

const dateInput = document.getElementById("date-input");
const doctorSelect = document.getElementById("doctor-select");
const doctorFilterGroup = document.getElementById("doctor-filter-group");
const tableWrap = document.getElementById("table-wrap");
const tbody = document.getElementById("schedule-tbody");
const emptyMsg = document.getElementById("empty-msg");
const errorMsg = document.getElementById("error-msg");

let appointments = [];

function clearMessages() {
    errorMsg.hidden = true;
    emptyMsg.hidden = true;
}

function showError(message) {
    tableWrap.hidden = true;
    errorMsg.textContent = message;
    errorMsg.hidden = false;
}

function showEmpty(message) {
    tableWrap.hidden = true;
    emptyMsg.textContent = message;
    emptyMsg.hidden = false;
}

function doctorKey(a) {
    return `${a.doctor_first_name}|${a.doctor_last_name}`;
}

function renderDoctorOptions() {
    if (appointments.length === 0) {
        doctorFilterGroup.hidden = true;
        doctorSelect.innerHTML = 'Todos';
        return;
    }
    doctorFilterGroup.hidden = false;

    const seen = new Map();
    for (const a of appointments) {
        const key = doctorKey(a);
        if (!seen.has(key)) {
            seen.set(key, formatName(a.doctor_first_name, a.doctor_last_name));
        }
    }
    const options = [...seen.entries()]
        .map(([key, label]) => ({ key, label }))
        .sort((a, b) => a.label.localeCompare(b.label, "es"));

    const previous = doctorSelect.value;
    doctorSelect.innerHTML =
        'Todos' +
        options
            .map(
                (o) =>
                    `${escapeHtml(o.label)}`
            )
            .join("");

    if (previous && options.some((o) => o.key === previous)) {
        doctorSelect.value = previous;
    }
}

function renderTable() {
    const selected = doctorSelect.value;
    const filtered = selected
        ? appointments.filter((a) => doctorKey(a) === selected)
        : appointments;

    if (filtered.length === 0) {
        if (appointments.length === 0) {
            showEmpty("No hay citas registradas para esta fecha.");
        } else {
            showEmpty("No hay citas del médico seleccionado para esta fecha.");
        }
        return;
    }
    emptyMsg.hidden = true;
    tableWrap.hidden = false;

    tbody.innerHTML = filtered
        .map(
            (a) => `

                ${fmtTime(a.start_time)} – ${fmtTime(a.end_time)}
                ${escapeHtml(formatName(a.doctor_first_name, a.doctor_last_name))}
                ${escapeHtml(a.specialty_name)}
                ${escapeHtml(formatName(a.patient_first_name, a.patient_last_name))}
            `
        )
        .join("");
}

async function loadSchedule() {
    clearMessages();
    const dateStr = dateInput.value;
    if (!dateStr) {
        appointments = [];
        renderDoctorOptions();
        showEmpty("Seleccione una fecha para consultar la agenda.");
        return;
    }
    try {
        appointments = await apiGet(
            `/api/public-schedule?date=${encodeURIComponent(dateStr)}`
        );
    } catch (err) {
        appointments = [];
        renderDoctorOptions();
        showError(err.message || "No se pudo cargar la agenda.");
        return;
    }
    renderDoctorOptions();
    renderTable();
}

dateInput.addEventListener("change", loadSchedule);
doctorSelect.addEventListener("change", renderTable);

// --- Inicio ---
dateInput.value = todayIso();
loadSchedule();
```
**Decisiones:**

- Los tres helpers viven ahora en `api.js` junto a `escapeHtml` y `formatName`; se exportan y se importan en cada script que los usa. Comportamiento idéntico al anterior (misma lógica, mismos retornos).

- Tabla de pacientes: la celda de nacimiento pasa de `escapeHtml(p.birth_date || "")` a `escapeHtml(fmtDate(p.birth_date))`. `fmtDate` devuelve `""` si la fecha es null, así que se sigue mostrando vacío cuando no hay fecha; con fecha se ve `dd/mm/aaaa`. El `input type="date"` del formulario no cambia, sigue trabajando en ISO (`yyyy-mm-dd`).

- `appointments.js` ya no necesita `startsAt`/`hasStarted` locales con su propia copia de `fmtTime`; ahora llaman al helper importado.

- `new-appointment.js` ya no redefine `todayIso`/`fmtDate`; se usan los de `api.js` en `dateInput.min`, validación y `showSuccess`.

---