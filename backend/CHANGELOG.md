# Liforex Backend — Robustness Pass Changelog

Covers the 7-step review-and-fix pass across the backend you originally
uploaded. Every change below was made only to files you had already
written — nothing new was implemented, no empty stub files were filled in.

**Verification status, honestly:** Steps 1–4 were verified with real,
executable tests wherever the sandbox allowed it (several bugs — including
two I introduced myself while fixing things — were caught this way, not
just reasoned about). Steps 5 and 7 could not be executed directly (no
SQLAlchemy or FastAPI available in this environment) and need a real
`pytest` run on your machine to get full confirmation. Treat that as a
required next step, not optional.

---

## Step 1 — Database layer

**Problem:** `sources` and `documents` tables didn't exist at all. Confirmed
directly by inspecting `liforex.db` — only Alembic's own bookkeeping table
was present. Root cause: `sqlalchemy.dialects.postgresql.ARRAY`/`JSON` and
`server_default=sa.text('now()')` are Postgres-only and don't work against
SQLite, which was the configured default.

**Decision:** commit to Postgres for real (your call).

**Changes:**
- `app/config.py` — default `database_url` now points at local Postgres
  instead of silently falling back to a broken SQLite setup
- `app/models/document.py` — JSON type now matches what the migration
  actually created (generic `sa.JSON`, not the Postgres-specific dialect
  type — these had drifted apart); added the missing
  `UniqueConstraint(source_id, source_url)` that was imported but never
  applied, so nothing previously stopped the same URL being ingested twice
- `alembic/versions/b2f4c91a7e3d_add_documents_source_url_unique.py` — new
  migration applying that constraint (the old migrations were left alone,
  since they're already-applied history)

---

## Step 2 — Content extraction correctness and performance

**Changes to `app/content/extractor.py`:**
- Fixed comment-stripping loop indentation — was nested inside the
  tag-removal loop, re-scanning the whole document for HTML comments once
  per ignored tag name (8x redundant work per document, not just once)
- Removed the premature plain-`<title>`-tag assignment that was silently
  blocking the richer JSON-LD/Open-Graph title logic from ever winning
- Broadened content-type check to accept `application/xhtml+xml` alongside
  `text/html` (real, valid, BeautifulSoup-parseable HTML that was
  previously dropped entirely)

**Changes to `app/content/metadata.py`:**
- Rewrote `extract_metadata()`'s priority logic — previously each source
  (plain tag, Open Graph, JSON-LD) was applied in sequence with an "only if
  still unset" check, but the plain-tag values were computed and assigned
  *first*, so they always won by default regardless of whether a better
  JSON-LD or OG value existed. Now computes all candidates first, then
  picks by explicit priority (JSON-LD > Open Graph > plain tag)
- `_apply_json_ld_overrides` (mutate-in-place) replaced with
  `_json_ld_fields` (pure function returning candidates), matching the new
  centralized priority logic
- Added RFC 2822 date parsing as a fallback when ISO-8601 doesn't match
  (common in feed-adjacent meta tags; previously silently returned `None`)
- Removed a `.astimezone()` call that was silently converting parsed dates
  to the *server's local timezone* — non-deterministic depending on where
  the code runs; now preserves the original offset, correct for a
  `DateTime(timezone=True)` column

**Verified with real, executable tests** (not just reasoning): title
priority across all three source tiers, RFC 2822 vs. ISO vs. garbage date
parsing, and comment/script/style stripping correctness.

---

## Step 3 — Deduplication's misleading function

**Problem:** `fingerprint_document_content()` was publicly exported and
named as if it returned a hash, but actually returned raw normalized
*text*. `fingerprint_document()` then hashed that text a second time
internally. Anything calling the public function directly would get back a
potentially huge string instead of a compact fingerprint.

**Changes to `app/content/deduplication.py`:**
- `fingerprint_document_content()` now actually returns a SHA-256 hash
- `fingerprint_document()` delegates to it instead of double-hashing

**Changes to `tests/content/test_deduplication.py`:**
- One existing assertion explicitly depended on the old buggy behavior
  (manually re-hashing the function's output) — updated to match the
  corrected relationship, and the now-unused `hashlib` import removed

**Verified** by re-running the real test assertions against the fixed code.

---

## Step 4 — Hardening the crawler for real-world sites

**Changes to `app/crawler/policy.py`:**
- Same-origin check now treats http/https as equivalent for the same host.
  Previously, a source registered as `http://example.gov` whose site
  redirects everything to `https://` (the default behavior of nearly all
  real .gov/.edu sites today) would have every single fetch rejected as
  `CROSS_ORIGIN`, purely because the scheme changed. New `_site()` method
  compares host+normalized-port instead of exact scheme+host+port; an
  explicit non-default port is still correctly treated as a real
  difference, not just a scheme upgrade

**Changes to `app/crawler/execution.py`:**
- `max_depth` is now actually enforced — it was defined on `CrawlRequest`
  but never read anywhere; `BoundedCrawlExecutor` only bounded by total
  page count, so a crawl could wander arbitrarily far from the seed URL
  before exhausting its page budget. Defaults to `None` (unlimited, the
  previous behavior) so nothing changes unless explicitly set
- Caught and fixed a bug in my own first attempt: `max_depth=0` was still
  fetching one extra layer of links, because the depth check only gated
  whether to *enqueue* further candidates, not whether to *fetch* the
  currently popped one

**Changes to `app/crawler/fetcher.py`:**
- Added retry with exponential backoff, `Retry-After` header respect, and
  per-host rate-limiting — previously a single transient timeout gave up
  permanently, and nothing throttled request frequency to a host (exactly
  what tends to trigger the 429s the code already anticipated handling).
  **All default to off** (0 retries, no rate limit) specifically so
  existing tests — several of which call `.fetch()` once and expect
  exactly one result with no delay — see zero behavior change unless
  explicitly opted into
- Caught and fixed a bug in my own refactor: a leftover line was silently
  resetting the retry timer's start time on every attempt instead of
  preserving it across the whole operation

**Verified with real, executable tests**, including against the actual
(unstubbed) `execution.py`/`orchestrator.py` modules, which turned out not
to need httpx or pydantic at all. All 6 pre-existing execution tests
re-run with zero regressions. New permanent test coverage added to all
three test files.

---

## Step 5 — Repository layer's race condition and scalability

**Problem:** `upsert()` checked `get_by_fingerprint()` *then* called
`create()` — a classic check-then-act race. Under concurrent access, two
workers processing identical content simultaneously could both pass the
check before either had inserted; the second would then hit the unique
constraint and get reported as `PERSISTENCE_FAILED` instead of the correct
`DUPLICATE`. Also: `count()`/`count_by_source()` loaded every row into
memory just to return a number, and `get_all_by_source()` was unbounded.

**Changes to `app/services/document_repository.py`:**
- `upsert()` rewritten to insert-first, catch the actual database
  conflict, and only then look up what's there — the database's own unique
  constraint is now the single source of truth. Correctly distinguishes a
  genuine fingerprint duplicate from a conflict caused by something else
  (like the new source_id+source_url constraint from Step 1) by confirming
  a matching row actually exists before treating it as a duplicate
- `upsert()` now returns `(document, created)` instead of just the
  document, so callers don't need their own separate pre-check
- `count()`/`count_by_source()` now use real SQL `COUNT` instead of
  `len(...all())`
- `get_all_by_source()` now paginated (default 100 per page)

**Changes to `app/pipeline/pipeline.py`:** one necessary compatibility
fix — updated the single `upsert()` call site to unpack the new tuple
return, which also naturally removed the pipeline's own redundant
duplicate-lookup query in the process.

**Changes to `tests/content/test_document_repository.py`:** 3 tests that
called `upsert()` directly updated to unpack the new tuple, each
strengthened with a real assertion on the new `created` flag.

**Not independently verified by me** — no SQLAlchemy available in this
sandbox. The "rollback, then keep using the same session" pattern this
relies on is already proven in your own `test_transaction_rollback_on_integrity_error`
test, which gives real confidence, but you need to run `pytest` yourself
to confirm this fully.

---

## Step 6 — Pipeline's remaining redundant work

**Changes to `app/pipeline/pipeline.py`:**
- Removed the entirely redundant metadata re-extraction step — Step 2
  (`extract_document()`) already applies metadata correctly as of Step 2's
  fix, so this second pass could never find anything the first pass hadn't
  already set. Was pure wasted work on every single document
- Step 4 (classify) now has the same try/except pattern as its neighbors —
  previously the one step that could crash the entire `process_url()` call
  on an unexpected error instead of degrading gracefully
- Docstring's step-by-step flow corrected to match reality
- 4 unused imports removed (`extract_metadata`, `CrawlOperationResult`,
  `Document`, `CrawlSource`) — found via a systematic check of every
  remaining import, not just the obvious one

**Changes to `app/pipeline/README.md`:** this had drifted in several
specific, checkable ways beyond the architecture diagram — corrected the
"Duplicate Detection" section (was describing the old, racy check-then-act
behavior as current), the component list (still cited a separate metadata
call), the database schema snippet (missing the Step 1 constraint), and
the logging section (quoted exact log message strings that no longer
matched the code).

**`tests/pipeline/test_pipeline.py` needed zero changes** — verified first:
every test asserts on final outcomes, not internal mechanics, so removing
redundant work didn't change anything they check.

---

## Step 7 — API layer pagination

**Changes to `app/api/sources.py`:** `list_sources` now takes
`limit`/`offset` query parameters via FastAPI's `Query()` validation
(default 100, capped at 1000) instead of returning every source
unconditionally.

**Changes to `tests/api/test_sources.py`:** new tests for parameter
validation. **Important finding, not a fix:** `SourceSession`, the
hand-rolled fake this file uses instead of a real database, completely
ignores whatever query statement it's given and always returns every
source. This means the test file genuinely cannot verify pagination
actually limits results — only that valid/invalid parameter values are
accepted or rejected. Confirming real `LIMIT`/`OFFSET` behavior needs a
real database session, the way `test_document_repository.py` already does
it with an actual SQLite engine instead of a fake object. Worth upgrading
this test file to that same pattern at some point.

---

## What's still open (flagged along the way, deliberately out of scope
for this pass — you asked to only touch files you'd already written)

- **No PDF support** — `app/ingestion/pdf_parser.py` is still an empty
  stub, and a meaningful chunk of real government/finance sources (CFTC
  advisories, IMF papers, SEC filings) are PDF
- **No JavaScript rendering** — pure `httpx` fetch only; JS-heavy sites
  will silently return near-empty content
- **Deduplication is exact-hash only** — won't catch the same content
  mirrored across sites with a different footer, or a lightly re-edited
  republish
- **`requirements.txt` has no version pins**
- **`trust_level`/`license`/`content_type` are free-form strings**, not
  constrained values — typos across many manually-added sources won't be
  caught
- All the empty model/API stub files (`concept.py`, `evidence.py`,
  `glossary.py`, `lesson.py`, `puzzle.py`, `question.py`,
  `relationship.py`, and the corresponding empty API routes) — genuinely
  unimplemented, not broken, just not yet written
