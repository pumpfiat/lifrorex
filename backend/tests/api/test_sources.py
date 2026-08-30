from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.db.database import get_db
from app.main import app
from app.models.source import Source


class SourceScalarResult:
	def __init__(self, sources: list[Source]) -> None:
		self.sources = sources

	def all(self) -> list[Source]:
		return self.sources


class SourceSession:
	def __init__(self, sources: list[Source], commit_error: IntegrityError | None = None) -> None:
		self.sources = sources
		self.commit_error = commit_error
		self.pending_source: Source | None = None
		self.source_snapshots: dict[int, dict[str, object]] = {}
		self.rolled_back = False

	def scalars(self, statement: object) -> SourceScalarResult:
		return SourceScalarResult(self.sources)

	def scalar(self, statement: object) -> Source | None:
		statement_parameters = statement.compile().params
		source_id = next(iter(statement_parameters.values()))
		return next((source for source in self.sources if source.id == source_id), None)

	def add(self, source: Source) -> None:
		self.pending_source = source

	def commit(self) -> None:
		if self.commit_error is not None:
			raise self.commit_error
		if self.pending_source is not None:
			self.pending_source.id = len(self.sources) + 1
			self.pending_source.created_at = datetime.now(timezone.utc)
			self.pending_source.updated_at = self.pending_source.created_at
			self.sources.append(self.pending_source)
			self.pending_source = None
		for source in self.sources:
			if source.id is not None:
				self.source_snapshots[source.id] = {
					"name": source.name,
					"url": source.url,
					"categories": source.categories,
					"trust_level": source.trust_level,
					"license": source.license,
					"crawl_allowed": source.crawl_allowed,
					"active": source.active,
				}

	def refresh(self, source: Source) -> None:
		pass

	def rollback(self) -> None:
		self.rolled_back = True
		self.pending_source = None
		for source in self.sources:
			if source.id is not None and source.id in self.source_snapshots:
				for field, value in self.source_snapshots[source.id].items():
					setattr(source, field, value)


def test_list_sources_returns_cftc() -> None:
	now = datetime.now(timezone.utc)
	source = Source(
		id=1,
		name="CFTC",
		url="https://www.cftc.gov/",
		categories=["forex", "markets", "risk", "regulation"],
		trust_level="primary",
		license="government",
		crawl_allowed=False,
		active=True,
		created_at=now,
		updated_at=now,
	)

	app.dependency_overrides[get_db] = lambda: SourceSession([source])
	try:
		response = TestClient(app).get("/sources")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 200
	assert response.json() == [
		{
			"id": 1,
			"name": "CFTC",
			"url": "https://www.cftc.gov/",
			"categories": ["forex", "markets", "risk", "regulation"],
			"trust_level": "primary",
			"license": "government",
			"crawl_allowed": False,
			"active": True,
			"created_at": now.isoformat().replace("+00:00", "Z"),
			"updated_at": now.isoformat().replace("+00:00", "Z"),
		}
	]


def test_list_sources_returns_empty_list() -> None:
	app.dependency_overrides[get_db] = lambda: SourceSession([])
	try:
		response = TestClient(app).get("/sources")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 200
	assert response.json() == []


def test_get_source_returns_cftc() -> None:
	now = datetime.now(timezone.utc)
	source = Source(
		id=1,
		name="CFTC",
		url="https://www.cftc.gov/",
		categories=["forex", "markets", "risk", "regulation"],
		trust_level="primary",
		license="government",
		crawl_allowed=False,
		active=True,
		created_at=now,
		updated_at=now,
	)

	app.dependency_overrides[get_db] = lambda: SourceSession([source])
	try:
		response = TestClient(app).get("/sources/1")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 200
	response_source = response.json()
	assert response_source["id"] == 1
	assert response_source["name"] == "CFTC"
	assert response_source["url"] == "https://www.cftc.gov/"
	assert response_source["categories"] == ["forex", "markets", "risk", "regulation"]
	assert response_source["trust_level"] == "primary"
	assert response_source["license"] == "government"
	assert response_source["crawl_allowed"] is False
	assert response_source["active"] is True
	assert "created_at" in response_source
	assert "updated_at" in response_source


def test_get_source_returns_not_found_for_missing_id() -> None:
	app.dependency_overrides[get_db] = lambda: SourceSession([])
	try:
		response = TestClient(app).get("/sources/999999")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 404
	assert response.json() == {"detail": "Source not found"}


def test_get_source_rejects_invalid_id() -> None:
	response = TestClient(app).get("/sources/not-an-integer")

	assert response.status_code == 422


def test_create_source_persists_and_returns_defaults() -> None:
	session = SourceSession([])
	app.dependency_overrides[get_db] = lambda: session
	try:
		response = TestClient(app).post(
			"/sources",
			json={
				"name": "Test Source",
				"url": "https://example.test/",
				"categories": ["testing"],
				"trust_level": "test",
				"license": "test",
			},
		)
		created_id = response.json()["id"]
		persisted_response = TestClient(app).get(f"/sources/{created_id}")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 201
	assert response.json()["name"] == "Test Source"
	assert response.json()["url"] == "https://example.test/"
	assert response.json()["categories"] == ["testing"]
	assert response.json()["trust_level"] == "test"
	assert response.json()["license"] == "test"
	assert response.json()["crawl_allowed"] is False
	assert response.json()["active"] is True
	assert response.json()["created_at"]
	assert response.json()["updated_at"]
	assert persisted_response.status_code == 200
	assert persisted_response.json()["id"] == created_id


def test_create_source_returns_conflict_and_rolls_back() -> None:
	cftc = Source(
		id=1,
		name="CFTC",
		url="https://www.cftc.gov/",
		categories=["forex", "markets", "risk", "regulation"],
		trust_level="primary",
		license="government",
		crawl_allowed=False,
		active=True,
		created_at=datetime.now(timezone.utc),
		updated_at=datetime.now(timezone.utc),
	)
	session = SourceSession([cftc], IntegrityError("duplicate URL", {}, Exception()))
	app.dependency_overrides[get_db] = lambda: session
	try:
		response = TestClient(app).post(
			"/sources",
			json={
				"name": "Duplicate CFTC",
				"url": "https://www.cftc.gov/",
				"categories": ["testing"],
				"trust_level": "test",
				"license": "test",
			},
		)
		list_response = TestClient(app).get("/sources")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 409
	assert response.json() == {"detail": "Source with this URL already exists"}
	assert session.rolled_back is True
	assert list_response.status_code == 200


def test_create_source_rejects_invalid_data() -> None:
	client = TestClient(app)

	assert client.post("/sources", json={}).status_code == 422
	assert client.post(
		"/sources",
		json={
			"name": "Test Source",
			"url": "https://example.test/",
			"categories": "testing",
			"trust_level": "test",
			"license": "test",
		},
	).status_code == 422


def make_test_source(id: int = 1, url: str = "https://example.test/") -> Source:
	now = datetime.now(timezone.utc)
	return Source(
		id=id,
		name="Test Source",
		url=url,
		categories=["testing"],
		trust_level="test",
		license="test",
		crawl_allowed=False,
		active=True,
		created_at=now,
		updated_at=now,
	)


def test_update_source_supports_partial_updates_and_persistence() -> None:
	source = make_test_source()
	session = SourceSession([source])
	session.commit()
	app.dependency_overrides[get_db] = lambda: session
	try:
		deactivated = TestClient(app).patch("/sources/1", json={"active": False})
		reactivated = TestClient(app).patch("/sources/1", json={"active": True})
		single_field = TestClient(app).patch("/sources/1", json={"name": "Updated Source"})
		multiple_fields = TestClient(app).patch(
			"/sources/1",
			json={
				"name": "Updated Source",
				"categories": ["markets", "education"],
				"trust_level": "secondary",
				"active": False,
			},
		)
		persisted = TestClient(app).get("/sources/1")
	finally:
		app.dependency_overrides.clear()

	assert deactivated.status_code == 200
	assert deactivated.json()["active"] is False
	assert deactivated.json()["url"] == "https://example.test/"
	assert reactivated.status_code == 200
	assert reactivated.json()["active"] is True
	assert single_field.status_code == 200
	assert single_field.json()["name"] == "Updated Source"
	assert single_field.json()["categories"] == ["testing"]
	assert multiple_fields.status_code == 200
	assert multiple_fields.json()["categories"] == ["markets", "education"]
	assert multiple_fields.json()["trust_level"] == "secondary"
	assert multiple_fields.json()["active"] is False
	assert multiple_fields.json()["url"] == "https://example.test/"
	assert persisted.status_code == 200
	assert persisted.json()["active"] is False


def test_update_source_handles_missing_invalid_empty_and_null_payloads() -> None:
	source = make_test_source()
	session = SourceSession([source])
	session.commit()
	app.dependency_overrides[get_db] = lambda: session
	try:
		missing = TestClient(app).patch("/sources/999999", json={"active": False})
		empty = TestClient(app).patch("/sources/1", json={})
		null = TestClient(app).patch("/sources/1", json={"active": None})
		invalid_id = TestClient(app).patch("/sources/not-an-integer", json={"active": False})
	finally:
		app.dependency_overrides.clear()

	assert missing.status_code == 404
	assert missing.json() == {"detail": "Source not found"}
	assert empty.status_code == 200
	assert empty.json()["active"] is True
	assert null.status_code == 422
	assert invalid_id.status_code == 422


def test_update_source_rolls_back_duplicate_url_conflict() -> None:
	source = make_test_source()
	session = SourceSession([source], IntegrityError("duplicate URL", {}, Exception()))
	session.commit_error = None
	session.commit()
	session.commit_error = IntegrityError("duplicate URL", {}, Exception())
	app.dependency_overrides[get_db] = lambda: session
	try:
		response = TestClient(app).patch("/sources/1", json={"url": "https://existing.test/"})
		follow_up = TestClient(app).get("/sources/1")
	finally:
		app.dependency_overrides.clear()

	assert response.status_code == 409
	assert response.json() == {"detail": "Source with this URL already exists"}
	assert session.rolled_back is True
	assert follow_up.status_code == 200
	assert follow_up.json()["url"] == "https://example.test/"


def test_archive_source_is_idempotent_and_preserves_the_record() -> None:
	source = make_test_source()
	session = SourceSession([source])
	session.commit()
	app.dependency_overrides[get_db] = lambda: session
	try:
		first_archive = TestClient(app).post("/sources/1/archive")
		read_after_archive = TestClient(app).get("/sources/1")
		list_after_archive = TestClient(app).get("/sources")
		second_archive = TestClient(app).post("/sources/1/archive")
		reactivated = TestClient(app).patch("/sources/1", json={"active": True})
	finally:
		app.dependency_overrides.clear()

	assert first_archive.status_code == 200
	assert first_archive.json()["active"] is False
	assert first_archive.json()["name"] == "Test Source"
	assert first_archive.json()["url"] == "https://example.test/"
	assert first_archive.json()["categories"] == ["testing"]
	assert first_archive.json()["trust_level"] == "test"
	assert first_archive.json()["license"] == "test"
	assert first_archive.json()["crawl_allowed"] is False
	assert read_after_archive.status_code == 200
	assert read_after_archive.json()["active"] is False
	assert list_after_archive.status_code == 200
	assert list_after_archive.json()[0]["active"] is False
	assert second_archive.status_code == 200
	assert second_archive.json()["active"] is False
	assert reactivated.status_code == 200
	assert reactivated.json()["active"] is True


def test_archive_source_handles_missing_and_invalid_ids() -> None:
	source = make_test_source()
	session = SourceSession([source])
	session.commit()
	app.dependency_overrides[get_db] = lambda: session
	try:
		missing = TestClient(app).post("/sources/999999/archive")
		invalid_id = TestClient(app).post("/sources/not-an-integer/archive")
	finally:
		app.dependency_overrides.clear()

	assert missing.status_code == 404
	assert missing.json() == {"detail": "Source not found"}
	assert invalid_id.status_code == 422