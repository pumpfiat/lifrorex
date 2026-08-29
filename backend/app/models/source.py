from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Source(Base):
	__tablename__ = "sources"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	name: Mapped[str] = mapped_column(String, nullable=False)
	url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
	categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
	trust_level: Mapped[str] = mapped_column(String, nullable=False)
	license: Mapped[str] = mapped_column(String, nullable=False)
	crawl_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
	active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)
