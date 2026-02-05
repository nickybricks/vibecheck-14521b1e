# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-05)

**Core value:** Users can see how sentiment around AI models and tools has changed over time, with clear time-series data powered by real news and Reddit community opinion.
**Current focus:** Phase 3: API Integration

## Current Position

Phase: 3 of 3 (API Integration)
Plan: 03-02 of 10 (Sentiment Time-Series Query)
Status: In progress
Last activity: 2026-02-05 — Completed sentiment time-series query endpoint with cursor pagination

Progress: [██░░░░░░░░] 20% (2 of 10 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 3.3 min
- Total execution time: 0.5 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-storage | 3 | 9 min | 3 min |
| 02-data-pipeline | 4 | 18 min | 4.5 min |
| 03-api-integration | 2 | 6 min | 3 min |

**Recent Trend:**
- Last 5 plans: 02-04 (12 min), 03-01 (3 min), 03-02 (4 min)
- Trend: Phase 3 API integration proceeding smoothly with consistent velocity

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

**From 03-02 (2026-02-05):**
- Use cursor-based pagination with ISO timestamp for time-series data (newest first, cursor queries data before timestamp)
- Query latest daily sentiment for entity detail using subquery with ORDER BY timestamp DESC LIMIT 1
- Filter by period parameter ('hourly' or 'daily') to support multiple granularities
- Return empty data array when no time-series data exists (not 404) - semantically correct for API consumers
- Let FastAPI handle datetime validation (400 on invalid ISO format) instead of custom parsing
- Pydantic v2 ORM conversion pattern: Create dict with extra fields, then model_validate() (kwargs not supported)

**From 03-01 (2026-02-05):**
- Use EntitySchema for list responses, EntityDetailSchema for detail responses (separation for extensibility)
- latest_sentiment field in EntityDetailSchema left as None with TODO (populated in plan 03-02 from SentimentTimeseries)
- HTTPException with status_code=404 and descriptive detail message for API error handling
- FastAPI router pattern with prefix and tags for OpenAPI organization
- Async session dependency injection via Depends(get_session) for database access
- ORM model to Pydantic schema conversion using model_validate() with from_attributes=True
- Scalar queries with scalar_one_or_none() for single entity lookups

**From 03-03 (2026-02-05):**
- Use ENVIRONMENT variable to switch CORS behavior (development vs production)
- Parse CORS_ORIGINS as comma-separated string for multiple domain support
- Log allowed origins in development mode (print() for startup logging before structured logging)
- Cache preflight responses for 1 hour (max_age=3600) to reduce OPTIONS requests
- Explicitly list HTTP methods instead of wildcard for better security documentation
- Enable allow_credentials=True for future cookie-based authentication
- Expose Content-Range header for future pagination support

**From 02-04 (2026-02-05):**
- Use AsyncIOScheduler with interval triggers (15min news, 60min stories) rather than cron for simplicity
- Track last_run in memory (job_last_run dict) for fast health checks without database query
- Health threshold: job is overdue if not run within 2x its interval (30min for news, 120min for stories)
- Graceful shutdown with scheduler.shutdown(wait=True) to complete running jobs before FastAPI stops
- Module-level scheduler instance shared across lifespan and health endpoint for singleton pattern
- Job wrapper pattern adds audit logging to any async job function
- Health endpoint returns 503 Service Unavailable when scheduler unhealthy, 200 when healthy

**From Pre-Phase 3 (2026-02-05):**
- Use AsyncAskNewsSDK (not sync AskNewsSDK) for async-first integration with FastAPI
- API key authentication via custom httpx.Auth class (Bearer token injection)
- SDK parameters: n_articles (not limit) for news search, return_type='dicts' for Pydantic models
- Pydantic model responses use attribute access (item.title) not dict access (item.get("title"))
- AskNews StoryResponse structure: uuid (story_id), topic (headline), sentiment + sentiment_timestamps arrays
- Reddit data comes from StoryResponseUpdate.reddit_threads in updates[0] (latest update)

**From 02-03 (2026-02-05):**
- Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING for time-series deduplication
- Extract Reddit sentiment as separate field rather than blending with overall sentiment
- Continue job execution on per-entity failures to maximize data collection
- Retry only on transient network errors (TimeoutError, ConnectionError) not API validation errors
- Log first story response at INFO level for API validation without overwhelming logs

**From 02-02 (2026-02-05):**
- Primary deduplication via external_id, secondary via SHA256 URL hash
- Exponential backoff: 3 attempts, 1s-16s wait, retry on TimeoutError/ConnectionError only
- Per-entity error handling: job continues processing remaining entities even if one fails
- Non-curated entities silently filtered during normalization (no exceptions)
- Sentiment label-to-score mapping: positive=0.5, negative=-0.5, neutral=0.0
- Datetime parsing with timezone handling and fallback to utcnow() for resilience

**From 02-01 (2026-02-05):**
- Use AskNews SDK OAuth2 with scopes=['news', 'stories'] for minimal permission surface
- Bidirectional substring matching for entity variations (handles partial matches like 'OpenAI GPT-4o')
- Entity normalization returns None for non-curated entities (no exceptions)
- Exception propagation in AskNews client for retry handling in jobs layer
- ENTITY_VARIATIONS covers all 10 curated entities with 5+ variations each

**From 01-03 (2026-02-05):**
- Use FastAPI lifespan context manager for database initialization (startup creates tables, shutdown disposes engine)
- Health endpoint includes database connectivity test via SELECT 1 query
- Curated entity list matches PROJECT.md specification (5 models + 5 tools)
- All import paths use relative imports (db.* not backend.db.*) for Docker container compatibility
- ~~CORS allows all origins in development (must be restricted in production)~~ **UPDATED:** Replaced by environment-specific CORS in 03-03

**From 01-02 (2026-02-05):**
- Use expire_on_commit=False for async sessions to prevent implicit queries after commit
- Enable pool_pre_ping=True for connection verification to prevent stale connection errors
- Composite index on (entity_id, timestamp DESC) for efficient time-series queries
- Manual migration creation allows offline development without database connection

**From 01-01 (2026-02-05):**
- Use Docker Compose for local development with isolated PostgreSQL container
- PostgreSQL healthcheck prevents backend from starting before database is ready (service_healthy condition)
- Both pyproject.toml and requirements.txt for clarity
- Python 3.12 as base image (latest stable with strong async support)
- SQLAlchemy 2.0.35 with asyncpg driver for async-first database access

**From initial planning:**
- Hybrid AskNews approach (News Search + Story Clustering) for high-precision tracking with Reddit sentiment
- Use AskNews built-in sentiment (no custom NLP needed)
- Fixed curated entity list for controlled costs and consistent tracking
- PostgreSQL for time-series storage (TimescaleDB-compatible schema design)
- FastAPI backend with Python async support
- Scheduled polling (15 min news, 60 min stories) for predictable data collection

### Pending Todos

None yet.

### Blockers/Concerns

**Phase 1 Complete:**
- ✓ Schema design is TimescaleDB-compatible with composite (entity_id, timestamp DESC) index
- ✓ Docker Compose monorepo structure isolates frontend/ and backend/ directories
- ✓ SQLAlchemy async patterns use AsyncSession and AsyncEngine correctly with expire_on_commit=False
- ✓ Alembic env.py configured for async migrations with asyncio.run()
- ✓ FastAPI application with health endpoint and database connectivity verification
- ✓ CORS middleware configured for frontend integration
- ✓ Curated entity constants defined for Phase 2 filtering

**Phase 2 Complete:**
- ✓ AskNews SDK client with OAuth2 authentication operational
- ✓ Entity normalization service with variation mapping complete
- ✓ News polling job with retry logic and URL hash deduplication
- ✓ Article storage service with batch insert and entity normalization
- ✓ Story polling job with retry logic and per-entity error recovery
- ✓ Sentiment time-series service with Reddit data extraction
- ✓ APScheduler integration with FastAPI lifespan (startup/shutdown)
- ✓ Scheduler execution logging with SchedulerExecutionLog model
- ✓ Health endpoint for monitoring job execution status
- ✓ Job wrapper pattern with audit logging and error handling

**Before Phase 3:**
- ✓ ASKNEWS_API_KEY environment variable set and mounted in Docker container
- ✓ Entity seeding script created and tested (10 entities in database)
- ✓ Unique constraint on sentiment_timeseries(entity_id, timestamp, period) applied
- ✓ Automatic migrations configured in Docker entrypoint script
- ✓ AskNews SDK API key authentication implemented and tested
  - Created custom `APIKeyAuth` class using httpx.Auth
  - Switched from sync `AskNewsSDK` to `AsyncAskNewsSDK`
  - Fixed SDK parameter names (n_articles vs limit)
  - Verified with test: 2 news articles and 2 stories fetched successfully

**Phase 3 Progress:**
- ✓ Entity query endpoints implemented (03-01)
  - GET /entities returns all entities ordered by name
  - GET /entities/{id} returns single entity with 404 handling
  - Pydantic schemas (EntitySchema, EntityDetailSchema) for response validation
- ✓ Sentiment time-series query endpoint implemented (03-02)
  - GET /entities/{id}/sentiment with date range filtering (start_date, end_date)
  - Cursor-based pagination using ISO timestamp (next_cursor, has_more)
  - Period selection (hourly or daily) with regex validation
  - Entity existence check returns 404 for non-existent entities
  - latest_sentiment populated in entity detail via subquery (most recent daily sentiment)
- ✓ CORS middleware configured with environment-specific origins (03-03)
  - Development mode allows all origins with logging
  - Production mode supports comma-separated domain restrictions
  - Preflight caching enabled (1 hour max_age)
- ✓ .env.example documents all environment variables

## Session Continuity

Last session: 2026-02-05 (Phase 3 Plan 03-02: Sentiment Time-Series Query)
Stopped at: Completed sentiment time-series query endpoint with cursor pagination and date filtering
  - SentimentPointSchema and SentimentTimeseriesResponse with Pydantic v2 syntax
  - GET /entities/{id}/sentiment endpoint with cursor pagination (next_cursor, has_more)
  - Date range filtering (start_date, end_date) and period selection (hourly/daily)
  - latest_sentiment populated in entity detail via subquery
  - Entity and sentiment routers registered with FastAPI app
Resume file: .planning/phases/03-api-integration/03-02-SUMMARY.md

Config:
{
  "mode": "yolo",
  "depth": "quick",
  "parallelization": true,
  "commit_docs": true,
  "model_profile": "budget",
  "workflow": {
    "research": true,
    "plan_check": true,
    "verifier": true
  }
}
