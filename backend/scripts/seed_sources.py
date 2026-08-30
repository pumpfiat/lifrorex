from sqlalchemy import select

from app.db.database import SessionLocal
from app.models.source import Source


CFTC_URL = "https://www.cftc.gov/"


def main() -> None:
	session = SessionLocal()
	try:
		source = session.scalar(select(Source).where(Source.url == CFTC_URL))
		if source is None:
			source = Source(
				name="CFTC",
				url=CFTC_URL,
				categories=["forex", "markets", "risk", "regulation"],
				trust_level="primary",
				license="government",
				crawl_allowed=False,
				active=True,
			)
			session.add(source)
			session.commit()
			session.refresh(source)
			print(f"Inserted CFTC Source with id={source.id}")
		else:
			print(f"CFTC Source already exists with id={source.id}")

		verified_source = session.scalar(select(Source).where(Source.url == CFTC_URL))
		if verified_source is None:
			raise RuntimeError("CFTC Source could not be retrieved after insertion")

		print(
			{
				"id": verified_source.id,
				"name": verified_source.name,
				"url": verified_source.url,
				"categories": verified_source.categories,
				"trust_level": verified_source.trust_level,
				"license": verified_source.license,
				"crawl_allowed": verified_source.crawl_allowed,
				"active": verified_source.active,
				"created_at": verified_source.created_at,
				"updated_at": verified_source.updated_at,
			}
		)
	except Exception:
		session.rollback()
		raise
	finally:
		session.close()


if __name__ == "__main__":
	main()
