from pathlib import Path
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str = Field(default="123456789:TEST_TOKEN_HERE")
    ADMIN_IDS: List[int] = Field(default_factory=lambda: [123456789])
    DATABASE_PATH: str = Field(default="data/booking.db")

    SALON_NAME: str = Field(default="Beauty Studio Elegance")
    SALON_ADDRESS: str = Field(default="ул. Арбат, 25, Москва")
    SALON_PHONE: str = Field(default="+7 (999) 000-00-00")
    SALON_OPEN_HOUR: int = Field(default=10)
    SALON_CLOSE_HOUR: int = Field(default=20)
    SLOT_STEP_MINUTES: int = Field(default=30)
    TIMEZONE: str = Field(default="Europe/Moscow")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, (int, float)):
            return [int(v)]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []

    @property
    def db_path(self) -> Path:
        p = Path(self.DATABASE_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
