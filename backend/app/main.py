from fastapi import FastAPI
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db


app = FastAPI()


@app.get("/")
def root() -> dict[str, str]:
	return {"message": "Liforex Engine is running"}


@app.get("/health")
def health() -> dict[str, str]:
	return {"status": "ok", "service": "liforex-engine"}


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)) -> dict[str, str]:
	db.execute(text("SELECT 1")).scalar_one()
	return {"status": "ok", "database": "connected"}
