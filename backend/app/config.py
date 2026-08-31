from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=BACKEND_DIR / ".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	database_url: str = "sqlite:///./liforex.db"


settings = Settings()
