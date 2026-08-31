# Step 8H: Document Processing Pipeline

## Overview

The Document Processing Pipeline (Step 8H) orchestrates the complete workflow for processing URLs into quality-scored, deduplicated documents in the Liforex database.

## Architecture

```
URL + Source
    ↓
[1] Crawl (fetch HTML)
    ↓
[2] Extract Content (clean HTML → text)
    ↓
[3] Extract Metadata (title, description, author, dates, canonical URL)
    ↓
[4] Classify (regulation, guidance, enforcement, etc.)
    ↓
[5] Score Quality & Relevance (0-1 scores)
    ↓
[6] Fingerprint (SHA-256 of normalized content)
    ↓
[7] Deduplication Check (fingerprint already exists?)
    ↓
[8] Persist to Database
    ↓
ProcessingResult (CREATED|DUPLICATE|FETCH_FAILED|...)
```

## Key Features

### Duplicate Detection
- **Deterministic:** Same content always produces same fingerprint (SHA-256)
- **Before Persist:** Checks for existing fingerprint before attempting insert
- **Status Returned:** Returns `DUPLICATE` status without creating new record
- **Idempotent:** Processing same URL twice is safe

### Error Handling
- **Fetch Failures:** HTTP errors, timeouts, connection failures → `FETCH_FAILED`
- **Insufficient Content:** Less than 10 characters → `INSUFFICIENT_CONTENT`
- **Extraction Failures:** HTML parsing errors → `EXTRACTION_FAILED`
- **Non-HTML:** PDFs, images, etc. → `EXTRACTION_FAILED`
- **Persistence Errors:** Database constraint violations → `PERSISTENCE_FAILED`

### Metadata Enrichment
All extracted metadata automatically persisted:
- **Classification:** Document type + confidence level
- **Quality Score:** 0-1 scale (title quality, content depth, structure)
- **Relevance Score:** 0-1 scale (keyword matching, context)
- **Evidence Lists:** Why each score was assigned

## Usage

```python
from app.pipeline import DocumentProcessingPipeline
from app.crawler.orchestrator import SinglePageCrawlOrchestrator
from sqlalchemy.orm import Session

# Initialize
crawler = SinglePageCrawlOrchestrator(...)  # fully configured
session: Session = ...  # database session

pipeline = DocumentProcessingPipeline(crawler, session)

# Process a URL
source = session.query(Source).get(1)
result = pipeline.process_url(source, "https://example.com/report")

if result.status == ProcessingStatus.CREATED:
    print(f"New document created with ID {result.document_id}")
elif result.status == ProcessingStatus.DUPLICATE:
    print(f"Duplicate of document {result.document_id}")
elif result.status == ProcessingStatus.FETCH_FAILED:
    print(f"Fetch failed: {result.error_detail}")
```

## Processing Result

```python
@dataclass
class ProcessingResult:
    status: ProcessingStatus  # CREATED|DUPLICATE|FETCH_FAILED|...
    document_id: Optional[int]  # ID of created or existing document
    document_source_url: Optional[str]  # Final URL (after redirects)
    fingerprint: Optional[str]  # SHA-256 fingerprint (or None)
    error_detail: Optional[str]  # Error message if applicable
```

## Component Integration

- **Crawler:** Uses existing `SinglePageCrawlOrchestrator.crawl()`
- **Extraction:** Uses existing `extract_document()` from Step 8B
- **Metadata:** Uses existing `extract_metadata()` from Step 8C
- **Classification:** Uses existing `classify_document()` from Step 8D
- **Scoring:** Uses existing `score_document()` from Step 8E
- **Fingerprinting:** Uses existing `fingerprint_document()` from Step 8F
- **Persistence:** Uses existing `DocumentRepository.upsert()` from Step 8G

**No duplication:** Pipeline only orchestrates; all logic is in existing components.

## Database Schema

Uses existing Document table (Step 8G):

```sql
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE RESTRICT,
    source_url VARCHAR NOT NULL,
    canonical_url VARCHAR,
    title VARCHAR,
    description TEXT,
    author VARCHAR,
    published_at TIMESTAMP WITH TIME ZONE,
    modified_at TIMESTAMP WITH TIME ZONE,
    content TEXT NOT NULL,
    content_type VARCHAR,
    http_status INTEGER,
    extraction_status VARCHAR NOT NULL,
    meta JSON NOT NULL,  -- includes classification, scores, evidence
    fingerprint VARCHAR UNIQUE,  -- allows multiple NULLs
    fingerprint_version VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_documents_source_id ON documents(source_id);
CREATE INDEX ix_documents_fingerprint ON documents(fingerprint);
```

## Testing

```bash
# Run pipeline tests only
pytest tests/pipeline/test_pipeline.py -v

# Run with coverage
pytest tests/pipeline/test_pipeline.py --cov=app.pipeline

# Run full regression suite (includes pipeline)
pytest tests/ -v
```

**Test Database:** SQLite in-memory with foreign key enforcement (no external dependencies)

## Logging

Pipeline logs at INFO level:
- `Pipeline: crawling {url} from source {source_id}`
- `Pipeline: extracting content from {url}`
- `Pipeline: extracting metadata from {url}`
- `Pipeline: classifying document from {url}`
- `Pipeline: scoring document from {url}`
- `Pipeline: generating fingerprint for {url}`
- `Pipeline: persisting document from {url}`
- `Pipeline: document created with id {id} from {url}` or
- `Pipeline: duplicate document detected, existing id {id}`

Errors logged at ERROR level with exception details.

## Future Enhancements

- Batch processing (multiple URLs)
- Scheduled/async execution
- Retry logic for transient failures
- Pipeline execution metrics/monitoring
- Admin UI for pipeline control
- Source-specific configuration (crawl depth, extraction rules, etc.)
