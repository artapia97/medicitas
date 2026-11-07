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