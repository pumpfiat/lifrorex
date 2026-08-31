from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from app.db.database import get_db
from app.models.source import Source


router = APIRouter()


@router.post(
	"/sources", response_model=SourceResponse, status_code=status.HTTP_201_CREATED
)
def create_source(source_data: SourceCreate, db: Session = Depends(get_db)) -> Source:
	source = Source(**source_data.model_dump())
	db.add(source)
	try:
		db.commit()
		db.refresh(source)
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Source with this URL already exists",
		) from error
	return source


@router.patch("/sources/{id}", response_model=SourceResponse)
def update_source(
	id: int, source_data: SourceUpdate, db: Session = Depends(get_db)
) -> Source:
	source = db.scalar(select(Source).where(Source.id == id))
	if source is None:
		raise HTTPException(status_code=404, detail="Source not found")

	for field, value in source_data.model_dump(exclude_unset=True).items():
		setattr(source, field, value)

	try:
		db.commit()
		db.refresh(source)
	except IntegrityError as error:
		db.rollback()
		raise HTTPException(
			status_code=status.HTTP_409_CONFLICT,
			detail="Source with this URL already exists",
		) from error
	return source


@router.post("/sources/{id}/archive", response_model=SourceResponse)
def archive_source(id: int, db: Session = Depends(get_db)) -> Source:
	source = db.scalar(select(Source).where(Source.id == id))
	if source is None:
		raise HTTPException(status_code=404, detail="Source not found")

	source.active = False
	db.commit()
	db.refresh(source)
	return source


@router.get("/sources", response_model=list[SourceResponse])
def list_sources(
	limit: int = Query(default=100, gt=0, le=1000),
	offset: int = Query(default=0, ge=0),
	db: Session = Depends(get_db),
) -> list[Source]:
	# Previously unbounded -- returned every source in one response
	# regardless of how many existed. Same fix as
	# DocumentRepository.get_all_by_source() in Step 5. gt=0/le=1000 and
	# ge=0 give FastAPI's own request validation (422 on violation) instead
	# of hand-rolled checks.
	stmt = select(Source).order_by(Source.id).limit(limit).offset(offset)
	return list(db.scalars(stmt).all())


@router.get("/sources/{id}", response_model=SourceResponse)
def get_source(id: int, db: Session = Depends(get_db)) -> Source:
	source = db.scalar(select(Source).where(Source.id == id))
	if source is None:
		raise HTTPException(status_code=404, detail="Source not found")
	return source
