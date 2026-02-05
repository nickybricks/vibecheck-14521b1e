# Architecture Patterns

**Domain:** Python FastAPI backend with scheduled data pipeline + REST API
**Project:** VibeCheck sentiment tracking backend
**Researched:** 2026-02-05

## Recommended Architecture

The VibeCheck backend uses a **layered architecture** with **clear separation between the data pipeline (scheduled jobs) and the API server** to ensure scalability, maintainability, and resilience.

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vite/React)                    │
│                  (Handled by colleague)                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Server (FastAPI)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ HTTP Request Handlers (Routes & Endpoints)          │   │
│  │ - GET /api/entities                                 │   │
│  │ - GET /api/entities/{id}/sentiment                  │   │
│  │ - GET /api/articles                                 │   │
│  │ - GET /api/stories/{id}/details                     │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Service Layer (Business Logic)                       │   │
│  │ - SentimentQueryService                             │   │
│  │ - ArticleQueryService                               │   │
│  │ - StoryQueryService                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL Queries
                         ▼
┌─────────────────────────────────────────────────────────────┐
│            Data Access Layer (SQLAlchemy ORM)               │
│                  ┌─────────────────┐                        │
│                  │   Models        │                        │
│                  │ - Article       │                        │
│                  │ - Story         │                        │
│                  │ - RedditThread  │                        │
│                  │ - SentimentTs   │                        │
│                  └─────────────────┘                        │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL
                         ▼
          ┌──────────────────────────────────┐
          │    PostgreSQL Database           │
          │ - articles table                 │
          │ - stories table                  │
          │ - reddit_threads table           │
          │ - sentiment_timeseries table     │
          │ - entities table                 │
          └──────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│              Data Pipeline (Scheduled Jobs)                 │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ APScheduler (Scheduler)                             │   │
│  │ - News ingestion: every 15 minutes                  │   │
│  │ - Story ingestion: every 60 minutes                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Pipeline Service Layer (ETL Logic)                  │   │
│  │ - NewsIngestionService                             │   │
│  │ - StoryIngestionService                            │   │
│  │ - SentimentAggregationService                       │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ External API Integration                            │   │
│  │ - AskNewsClient (wraps SDK)                         │   │
│  └──────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────┘
                         │ SQL writes
                         ▼
          ┌──────────────────────────────────┐
          │    PostgreSQL Database           │
          │ (shared with API server)         │
          └──────────────────────────────────┘
                         ▲
                         │ API calls
        ┌────────────────┴────────────────┐
        ▼                                  ▼
   ┌──────────────┐              ┌──────────────────┐
   │ AskNews API  │              │ External Services│
   │ /news        │              │ (Auth, logging)  │
   │ /stories     │              └──────────────────┘
   └──────────────┘
```

## Component Boundaries

### 1. API Server (FastAPI Application)

**Responsibility:** Handle HTTP requests, serve data to frontend

**Location:** `backend/api/`

| Component | Role |
|-----------|------|
| `main.py` | FastAPI app initialization, CORS, middleware |
| `routes/` | HTTP endpoint handlers |
| `services/` | Query logic, data transformation |
| `schemas/` | Pydantic response models |

**Communicates with:**
- PostgreSQL (via SQLAlchemy)
- Pipeline (reads shared database, no direct communication)

**Key patterns:**
- Stateless request handlers
- Dependency injection for services
- Async request handling with `async def`

### 2. Data Access Layer (SQLAlchemy ORM)

**Responsibility:** Abstract database operations, manage models

**Location:** `backend/db/`

| Component | Role |
|-----------|------|
| `models.py` | SQLAlchemy model definitions |
| `session.py` | Database session management |
| `queries.py` | Reusable query builders (optional) |

**Communicates with:**
- PostgreSQL directly
- API services (read)
- Pipeline services (write)

### 3. Data Pipeline (APScheduler + Custom Services)

**Responsibility:** Ingest data on schedule, process, store to database

**Location:** `backend/pipeline/`

| Component | Role |
|-----------|------|
| `scheduler.py` | Job scheduling, timing |
| `jobs/` | Job definitions (news job, story job) |
| `services/` | Ingestion logic (fetch, parse, store) |
| `asknews_client.py` | AskNews API wrapper |

**Communicates with:**
- PostgreSQL (via SQLAlchemy)
- AskNews API (HTTP)
- Logging service

**Key patterns:**
- Idempotent job execution (can run safely multiple times)
- Error handling and retry logic
- Async I/O for API calls

### 4. Database (PostgreSQL)

**Responsibility:** Persist all data

**Shared access:** Both API and pipeline read/write

---

## Data Flow

### Request Flow (API → Frontend)

```
User opens React app
    ↓
Browser sends GET /api/entities/gpt4/sentiment?start=2026-01-01&end=2026-02-05
    ↓
FastAPI route handler (routes/entities.py)
    ↓
SentimentQueryService.get_sentiment_history(entity_id, start, end)
    ↓
SQLAlchemy ORM query: SELECT * FROM sentiment_timeseries WHERE entity_id=... AND timestamp >= ... AND timestamp <= ...
    ↓
PostgreSQL executes, returns rows
    ↓
ORM deserializes to SentimentPoint objects
    ↓
Service transforms to response schema
    ↓
FastAPI serializes to JSON, sends HTTP response
    ↓
Frontend renders chart
```

**Data stays:** In memory during request, serialized in response

### Ingestion Flow (Pipeline → Database)

```
APScheduler fires "ingest_news" job at HH:MM:00 (every 15 min)
    ↓
NewsIngestionJob.execute()
    ↓
AskNewsClient.fetch_news(entity_list) → calls AskNews API
    ↓
API returns articles with sentiment scores
    ↓
NewsIngestionService.process_and_store(articles)
    ├─ Parse sentiment, extract metadata
    ├─ Check for duplicates (avoid duplicate storage)
    ├─ SQLAlchemy: INSERT article rows into articles table
    ├─ SQLAlchemy: INSERT/UPDATE sentiment_timeseries rows
    └─ Commit transaction
    ↓
Log success/failure
    ↓
Next job queued for HH:MM+15
```

**Data stored:** Directly in PostgreSQL, durably persisted

---

## Scheduler: Same Process vs. Separate Process

### Recommendation: **START WITH SAME PROCESS** (single FastAPI app + scheduler)

**For VibeCheck development:** Run scheduler in the same process as the API server.

```python
# backend/main.py
from fastapi import FastAPI
from fastapi_utilities import repeat_every

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    scheduler = AsyncIOScheduler()

    # Add jobs
    scheduler.add_job(ingest_news_job, "interval", minutes=15, id="news_job")
    scheduler.add_job(ingest_stories_job, "interval", hours=1, id="stories_job")

    scheduler.start()

@app.get("/api/entities")
async def get_entities():
    # API endpoint
    ...
```

**Pros:**
- Simplicity: One Docker container, no orchestration
- Development ease: Single Python process to debug
- Cost: No extra infrastructure
- Fast startup: No inter-process communication

**Cons:**
- If scheduler hangs, API hangs (shared process)
- Harder to scale scheduler and API independently
- Limited by single process resources

### When to Migrate to Separate Process

**Migrate to Celery + separate workers** when:

1. **Scheduler latency affects API:** If long-running jobs slow down API requests
2. **Need independent scaling:** API and scheduler have different traffic patterns
3. **Production multi-replica:** Running multiple API instances (load balancing)

**Signs this is needed:**
- API p99 latency increases during ingestion jobs
- Need to scale pipeline without scaling API instances
- Jobs failing should not crash API server

---

## Suggested Build Order

### Phase 1: Foundation (Core Structure)
**Dependencies:** None

```
1. Database schema design
   - entities table
   - articles table
   - stories table
   - sentiment_timeseries table

2. SQLAlchemy ORM models
   - Map to schema

3. Database session management
   - Connection pooling

4. .env configuration
   - DB credentials
   - AskNews API keys
```

**Why first:** Everything depends on the database contract. Define schema before building services.

### Phase 2: API Server Scaffold
**Dependencies:** Phase 1 (database, models)

```
1. FastAPI application initialization
2. CORS middleware
3. Error handling
4. Logging setup
5. One stub endpoint (GET /api/health)
```

**Why early:** Get HTTP server running before adding complexity.

### Phase 3: AskNews Integration
**Dependencies:** Phase 1 (models)

```
1. AskNewsClient wrapper around SDK
2. fetch_news(entities) method
3. fetch_stories(entities) method
4. Error handling for API failures
5. Test with mock data
```

**Why here:** Data source needs testing before pipeline uses it.

### Phase 4: Data Pipeline
**Dependencies:** Phase 1, 2, 3

```
1. NewsIngestionService
   - Fetch news via AskNewsClient
   - Parse sentiment
   - Store to database

2. StoryIngestionService
   - Similar pattern

3. APScheduler setup
4. Job definitions
5. Manual job testing (no scheduler yet)
```

**Why after API:** Can test jobs manually without scheduler complexity.

### Phase 5: Scheduler Integration
**Dependencies:** Phase 1, 2, 3, 4

```
1. Add APScheduler to FastAPI startup
2. Register jobs
3. Start scheduler on app startup
4. Monitor job execution
```

**Why last:** Only needed after jobs are tested and working.

### Phase 6: API Endpoints
**Dependencies:** Phase 1, 2, 5

```
1. GET /api/entities (list)
2. GET /api/entities/{id}/sentiment (history)
3. GET /api/entities/compare (multiple)
4. GET /api/articles (search)
5. GET /api/stories/{id}/details
```

**Why last:** Wait until pipeline successfully stores data.

### Phase 7: Query Optimization
**Dependencies:** Phase 1, 6

```
1. Database indexes
2. Query optimization
3. Caching (if needed)
4. Load testing
```

**Why last:** Optimize based on actual usage patterns.

---

## Database Schema Design for Time-Series Sentiment Data

### Core Tables

#### `entities`
Curated list of AI models and tools.

```sql
CREATE TABLE entities (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,  -- e.g., "GPT-4o", "Claude"
    category VARCHAR(50) NOT NULL,      -- "model" or "tool"
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `articles`
News articles and Reddit threads fetched from AskNews.

```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE NOT NULL,  -- AskNews article ID
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source_name VARCHAR(255),
    source_url TEXT,
    published_at TIMESTAMP NOT NULL,
    fetched_at TIMESTAMP DEFAULT NOW(),
    sentiment_score NUMERIC(3, 2),  -- -1.0 to 1.0
    entities JSONB,  -- {"gpt4": true, "claude": true}

    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT sentiment_range CHECK (sentiment_score >= -1 AND sentiment_score <= 1)
);

CREATE INDEX idx_articles_published_at ON articles(published_at DESC);
CREATE INDEX idx_articles_fetched_at ON articles(fetched_at DESC);
CREATE INDEX idx_articles_external_id ON articles(external_id);
```

#### `stories`
Story clusters from AskNews with time-series sentiment.

```sql
CREATE TABLE stories (
    id UUID PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE NOT NULL,  -- AskNews story ID
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    entities JSONB,  -- {"gpt4": true, "claude": true}

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stories_external_id ON stories(external_id);
```

#### `sentiment_timeseries`
Time-series sentiment aggregates per entity (hourly and daily).

```sql
CREATE TABLE sentiment_timeseries (
    id UUID PRIMARY KEY,
    entity_id UUID NOT NULL REFERENCES entities(id),
    timestamp TIMESTAMP NOT NULL,  -- Start of period (hourly or daily)
    period VARCHAR(10) NOT NULL,   -- "hourly" or "daily"

    sentiment_mean NUMERIC(3, 2),
    sentiment_min NUMERIC(3, 2),
    sentiment_max NUMERIC(3, 2),
    sentiment_std NUMERIC(3, 2),

    source_type VARCHAR(20),  -- "news" or "reddit" (if separated)
    article_count INTEGER,

    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT sentiment_range CHECK (
        (sentiment_mean IS NULL OR sentiment_mean >= -1 AND sentiment_mean <= 1)
    )
);

CREATE INDEX idx_sentiment_ts_entity_timestamp ON sentiment_timeseries(entity_id, timestamp DESC);
CREATE INDEX idx_sentiment_ts_timestamp ON sentiment_timeseries(timestamp DESC);
```

#### `reddit_threads`
Reddit threads from AskNews story responses.

```sql
CREATE TABLE reddit_threads (
    id UUID PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE NOT NULL,
    story_id UUID NOT NULL REFERENCES stories(id),
    title VARCHAR(500),
    url TEXT,
    subreddit VARCHAR(255),
    sentiment_score NUMERIC(3, 2),
    fetched_at TIMESTAMP DEFAULT NOW(),

    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT sentiment_range CHECK (sentiment_score >= -1 AND sentiment_score <= 1)
);

CREATE INDEX idx_reddit_threads_story_id ON reddit_threads(story_id);
```

### Query Patterns

**Sentiment history for one entity:**
```sql
SELECT timestamp, sentiment_mean
FROM sentiment_timeseries
WHERE entity_id = $1 AND period = 'daily'
ORDER BY timestamp DESC
LIMIT 365;
```

**Compare two entities over time:**
```sql
SELECT
    s1.timestamp,
    s1.sentiment_mean AS entity1_sentiment,
    s2.sentiment_mean AS entity2_sentiment
FROM sentiment_timeseries s1
JOIN sentiment_timeseries s2
    ON s1.timestamp = s2.timestamp AND s1.period = s2.period
WHERE s1.entity_id = $1 AND s2.entity_id = $2
ORDER BY s1.timestamp DESC;
```

**Recent articles mentioning an entity:**
```sql
SELECT * FROM articles
WHERE entities @> jsonb_build_object('gpt4', true)
ORDER BY published_at DESC
LIMIT 20;
```

---

## Async Patterns: Scheduled Jobs + Request Handling

### Pattern 1: APScheduler with Async Jobs

**Background:** APScheduler can execute async functions using `AsyncIOScheduler`.

```python
# backend/pipeline/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from contextlib import asynccontextmanager

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app):
    # Startup
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()

# In FastAPI:
app = FastAPI(lifespan=lifespan)

# Jobs are async:
async def ingest_news_job():
    """Fetch and store articles every 15 minutes."""
    service = NewsIngestionService()
    await service.ingest_news()

scheduler.add_job(ingest_news_job, "interval", minutes=15)
```

**Why async:**
- Jobs can await AskNews API calls (non-blocking)
- API requests don't block while jobs run
- Better resource utilization

### Pattern 2: Thread Pool for Blocking Operations

**If any operation is blocking** (rare in modern Python):

```python
# Use ThreadPoolExecutor for blocking work
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=2)

async def ingest_news_job():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, blocking_operation)
```

**VibeCheck:** Not needed. AskNews SDK is async-friendly.

### Pattern 3: Exception Handling in Jobs

```python
async def ingest_news_job():
    try:
        service = NewsIngestionService()
        await service.ingest_news()
        logger.info("News ingestion completed successfully")
    except AskNewsAPIError as e:
        logger.error(f"API error: {e}")
        # Job fails gracefully, scheduler retries next cycle
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        # Alert ops, but don't crash scheduler
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
```

**Key:** Jobs should not crash the scheduler. Log errors and fail gracefully.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Blocking API Endpoints for Ingestion

**What goes wrong:**
```python
@app.get("/api/sync")
def manual_sync():
    # WRONG: Blocks all other requests
    ingest_news()  # Takes 5 seconds
    return {"status": "done"}
```

API becomes unresponsive during ingestion.

**Instead:** Run ingestion on schedule, don't block requests.

### Anti-Pattern 2: Shared Mutable State Between Scheduler and API

**What goes wrong:**
```python
# WRONG
cache = {}  # Global shared state

async def ingest_job():
    cache["last_update"] = datetime.now()

@app.get("/api/status")
def get_status():
    return {"last_update": cache.get("last_update")}
```

Race conditions, hard to debug.

**Instead:** Use database as single source of truth. Store state in `sentiment_timeseries`.

### Anti-Pattern 3: No Deduplication in Ingestion

**What goes wrong:**
```python
# WRONG: No check for duplicates
for article in fetched_articles:
    db.insert(article)  # Same article inserted 4 times (every 15 min)
```

Database fills with duplicates, queries become slow.

**Instead:** Check `external_id` uniqueness before insert.

```python
# CORRECT
for article in fetched_articles:
    existing = await db.query(Article).filter(
        Article.external_id == article.external_id
    ).first()
    if not existing:
        db.insert(article)
```

### Anti-Pattern 4: Synchronous I/O in Async Context

**What goes wrong:**
```python
async def ingest_news_job():
    # WRONG: Blocking HTTP call in async function
    response = requests.get(asknews_url)  # Blocks entire scheduler
    ...
```

Blocks scheduler and API concurrently.

**Instead:** Use async HTTP client.

```python
async def ingest_news_job():
    # CORRECT
    async with httpx.AsyncClient() as client:
        response = await client.get(asknews_url)
```

### Anti-Pattern 5: No Transaction Boundaries

**What goes wrong:**
```python
# WRONG: Partial writes if error occurs
db.insert(article)  # Success
db.insert(sentiment)  # Fails → article exists but sentiment doesn't
```

Data inconsistency.

**Instead:** Use transactions.

```python
async def ingest_news_job():
    async with db.transaction():
        await db.insert(article)
        await db.insert(sentiment)
        # Both succeed or both rollback
```

### Anti-Pattern 6: Unbounded Growth of `sentiment_timeseries`

**What goes wrong:**
```
Every 15 min: insert article
Every hour: insert 4 sentiment rows (one per entity)
With 5 entities: 20 rows/hour, 480 rows/day

But: What if you add more entities later?
Need to re-aggregate old data.
```

**Instead:** Design for growth.

1. Use `period` column to separate hourly/daily aggregates
2. Plan re-aggregation strategy (backfill old data when adding entities)
3. Set up data retention policy (archive old articles after X days)

---

## Scalability Considerations

| Concern | At 100 Users | At 10K Users | At 1M Users |
|---------|--------------|--------------|-------------|
| **API throughput** | Single FastAPI instance (1 core) | 2-4 instances, reverse proxy | 10+ instances, CDN, caching |
| **Scheduler** | Single APScheduler in FastAPI | Separate scheduler service | Distributed task queue (Celery) |
| **Database** | Single PostgreSQL (RDS micro) | RDS with read replicas | Partitioned by entity or time |
| **Storage** | <1 GB (6 months) | 10-50 GB | 100+ GB (retention policy) |
| **Sentiment aggregation** | Synchronous in job | Asynchronous pipeline | Real-time stream processing |

**For VibeCheck MVP:** Single instance architecture is sufficient.

---

## Deployment Implications

### Single Container (Recommended for Phase 1)

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Inside container:**
- FastAPI listening on port 8000
- APScheduler running in same process
- Jobs execute in the background
- API requests handled concurrently with async

**Deployment:**
```bash
docker run -e DATABASE_URL=... -p 8000:8000 vibecheck-backend
```

### Separate Containers (Phase 2, if needed)

```
Container 1: FastAPI API server (uvicorn)
Container 2: Scheduler (APScheduler or Celery worker)
Shared: PostgreSQL (managed service)
```

For VibeCheck, start with single container.

---

## Error Handling and Resilience

### Job Failures Don't Cascade

```python
# Schedule has built-in retry logic
scheduler.add_job(
    ingest_news_job,
    "interval",
    minutes=15,
    max_instances=1,  # Only one instance runs at a time
    coalesce=True,    # Skip missed runs if overloaded
)
```

### Failed API Requests

```python
async def ingest_news_job():
    try:
        articles = await asknews_client.fetch_news(entities)
    except httpx.TimeoutException:
        logger.warning("AskNews API timeout, will retry next cycle")
        return  # Job fails gracefully, next run in 15 min
    except httpx.HTTPError as e:
        if e.response.status_code == 429:
            logger.warning("Rate limited, backing off")
        raise  # Re-raise to alert monitoring
```

### Database Connection Pooling

```python
# SQLAlchemy handles connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,  # For serverless
    # OR
    pool_size=20,
    max_overflow=40,
)
```

---

## Directory Structure

```
backend/
├── main.py                 # FastAPI app, scheduler setup, lifespan
├── config.py              # Settings from .env
├── requirements.txt       # Python dependencies
│
├── api/
│   ├── routes/            # HTTP endpoints
│   │   ├── entities.py
│   │   ├── articles.py
│   │   └── stories.py
│   ├── schemas/           # Pydantic response models
│   │   ├── entity.py
│   │   ├── article.py
│   │   └── sentiment.py
│   └── services/          # Query business logic
│       ├── sentiment_service.py
│       ├── article_service.py
│       └── story_service.py
│
├── db/
│   ├── models.py          # SQLAlchemy ORM models
│   ├── session.py         # DB connection/session
│   └── migrations/        # Alembic migrations (optional)
│
├── pipeline/
│   ├── scheduler.py       # APScheduler setup
│   ├── jobs/              # Job definitions
│   │   ├── news_job.py
│   │   └── stories_job.py
│   ├── services/          # Ingestion business logic
│   │   ├── news_ingestion.py
│   │   ├── story_ingestion.py
│   │   └── sentiment_aggregation.py
│   └── asknews_client.py  # SDK wrapper
│
└── utils/
    ├── logging.py         # Logging setup
    ├── error_handling.py  # Custom exceptions
    └── constants.py       # Entity lists, etc.
```

---

## Key Decisions & Rationale

| Decision | Choice | Why |
|----------|--------|-----|
| **Scheduler location** | Same process as API | Simplicity for MVP. Migrate to separate container if needed. |
| **Async pattern** | APScheduler + AsyncIOScheduler | Native async support, no extra overhead |
| **ORM** | SQLAlchemy | Async support, mature, excellent PostgreSQL integration |
| **HTTP client** | httpx | Async, parallel requests, modern API |
| **Job framework** | APScheduler | Built-in retry, coalesce, less overhead than Celery |
| **Schema design** | Explicit `period` column in sentiment table | Allows hourly and daily aggregates, supports future roll-ups |
| **Deduplication** | Check `external_id` before insert | Idempotent, prevents duplicates from repeated job runs |
| **Transaction scope** | Per-job atomic | Ensures consistency, prevents partial writes |

---

## Sources

**Patterns & Best Practices:**
- FastAPI documentation: Asynchronous task patterns (training knowledge, current as Feb 2025)
- APScheduler documentation: Scheduler concepts and async support
- SQLAlchemy: Async engine and session patterns
- PostgreSQL: Time-series best practices

**VibeCheck Context:**
- PROJECT.md: AskNews API constraints, entity list, polling schedule
- Constraints: Single developer, greenfield backend, same repo as frontend

**Not researched via external sources:** Project constraints and internal documentation drove decisions. Architecture follows standard FastAPI + PostgreSQL patterns with time-series considerations.

