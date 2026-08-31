from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
	model_config = SettingsConfigDict(
		env_file=BACKEND_DIR / ".env",
		env_file_encoding="utf-8",
		extra="ignore",
	)

	# Postgres is the committed database for this project (see Source.categories'
	# use of the Postgres-only ARRAY type, and JSON handling elsewhere). This
	# default assumes a local Postgres instance is running -- see README/setup
	# notes for the one-line Docker command to start one. Override via a real
	# .env file for anything other than local development.
	database_url: str = "postgresql+psycopg://liforex:liforex@localhost:5432/liforex"


settings = Settings()
