# Liforex.org

Liforex is a forex-learning platform that combines a browser-based learning experience with a backend system for structured content and data management. The project includes:

- a frontend for lessons, practice, puzzles, community, and tools
- a FastAPI backend for app services and database-driven source management
- a foundation for market content ingestion, crawler, and knowledge-layer integrations

## What is in this project

### Frontend
The main site is built with plain HTML, CSS, and JavaScript and includes pages such as:

- homepage and navigation
- lesson content
- practice and puzzle modes
- community and tools pages
- shared data-driven content from JSON files and UI assets

This part is designed to be lightweight and easy to run locally without a framework build step.

### Backend
The backend is a FastAPI application in the `backend/` folder. It includes:

- application startup and health endpoints
- database configuration using SQLAlchemy
- source management APIs for creating, listing, updating, and archiving records
- PostgreSQL-ready schema definitions and Alembic migrations support
- app modules for crawler, ingestion, knowledge, market, puzzles, and services

The current backend includes a working API surface for source data and database health checks.

## Project structure

```text
liforex/
├── README.md
├── index.html
├── learn.html
├── practice.html
├── community.html
├── tools.html
├── css/
├── js/
├── data/
├── LICENSE
├── ATTRIBUTION.md
├── backend/
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/
│   ├── scripts/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── api/
│       ├── db/
│       ├── models/
│       ├── crawler/
│       ├── ingestion/
│       ├── knowledge/
│       ├── market/
│       ├── puzzles/
│       └── services/
└── ui/
```

## Current backend features

The backend currently exposes these major endpoints:

- `GET /` — app root
- `GET /health` — service health check
- `GET /health/database` — database connectivity check
- `POST /sources` — create a source record
- `GET /sources` — list sources
- `GET /sources/{id}` — fetch a source
- `PATCH /sources/{id}` — update a source
- `POST /sources/{id}/archive` — archive a source

The source model contains fields such as name, URL, categories, trust level, license, crawl permissions, active state, and timestamps.

## Local development

### Frontend
From the project root, run a simple local web server:

```bash
cd liforex
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

This is the easiest way to view the site because the pages load JSON content from the browser.

### Backend
From the backend folder:

```bash
cd liforex/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file with your database URL, for example:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/liforex
```

Then run:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

If you are running the frontend and backend at the same time, make sure they are bound to different ports or use a reverse proxy setup in development.

## Tech stack

- Frontend: HTML, CSS, JavaScript
- Backend: FastAPI, SQLAlchemy, Pydantic
- Database: PostgreSQL-ready configuration
- Migrations: Alembic
- Scraping / ingestion: BeautifulSoup and HTTPX
- Testing: Pytest

## Notes

This repository is more than just a static frontend. It includes a backend foundation for market data workflows, source tracking, and future content ingestion pipelines. The frontend and backend should be treated as two connected parts of the same product.

## License

This project is distributed under the AGPL-3.0 license. See `LICENSE` and `ATTRIBUTION.md` for more details.
