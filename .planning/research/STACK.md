# Technology Stack: VibeCheck Backend

**Project:** VibeCheck (Python data pipeline + FastAPI backend)
**Researched:** February 2026
**Knowledge Cutoff:** February 2025
**Overall Confidence:** MEDIUM-HIGH (FastAPI/SQLAlchemy HIGH, TimescaleDB choice MEDIUM, task scheduling MEDIUM)

## Recommended Stack

### Core Framework & API

| Technology | Version | Purpose | Why | Confidence |
|-----------|---------|---------|-----|------------|
| **FastAPI** | 0.115+ | REST API framework, async request handling | Modern async-first framework, automatic OpenAPI docs, excellent type hints support, ideal for data pipelines. Faster than Flask/Django for this use case. | HIGH |
| **Uvicorn** | 0.30+ | ASGI server | Standard, high-performance async server for FastAPI in production. Actively maintained. | HIGH |
| **Pydantic** | 2.7+ | Data validation & serialization | Built into FastAPI, excellent for request/response validation, including custom validators for sentiment scores (-1 to +1 range). | HIGH |
| **Python** | 3.11+ (target 3.12) | Runtime | 3.11 has excellent async/await support; 3.12 added performance improvements. FastAPI requires 3.8+, but 3.11+ recommended for production. | HIGH |

### Database & Data Layer

| Technology | Version | Purpose | Why | Confidence |
|-----------|---------|---------|-----|------------|
| **PostgreSQL** | 16+ | Primary data store | Time-series data via table design (not TimescaleDB for MVP). Better than alternatives because: excellent query performance for time-series aggregations, proven at scale, JSONB support for flexible sentiment/metadata storage. | HIGH |
| **SQLAlchemy** | 2.0+ (>=2.0.35) | ORM & database abstraction | Mature, async support via asyncpg, excellent migration tooling with Alembic. 2.0+ has cleaner syntax. Avoid SQLModel (thin wrapper, less mature). Better than Tortoise (not as battle-tested at scale). | HIGH |
| **asyncpg** | 0.30+ | PostgreSQL async driver | Fastest Python PostgreSQL driver; essential for non-blocking async queries with FastAPI. | HIGH |
| **Alembic** | 1.14+ | Database migrations | SQLAlchemy-integrated migration tool, essential for production deployments. | HIGH |

### Scheduled Tasks & Data Ingestion

| Technology | Version | Purpose | Why | Confidence |
|-----------|---------|---------|-----|------------|
| **APScheduler** | 3.10+ | Lightweight job scheduling | For 2 simple recurring tasks (news every 15min, stories hourly): APScheduler is sufficient and lighter-weight. Built-in backfill and persistence. No message broker needed at this scale (~100 jobs/day). | MEDIUM |
| **Background Tasks** | FastAPI built-in | Non-blocking background operations | Use FastAPI's BackgroundTasks for one-off operations (e.g., post-response cleanup). | HIGH |
| **Redis** (optional, Phase 2) | 7.0+ | Cache + job result storage | Consider for Phase 2 if you add WebSocket updates or distributed deployments. Skip for MVP. | N/A |

**Scheduling rationale:** APScheduler chosen over Celery because:
- Celery adds complexity (message broker, worker processes) not justified at 100 scheduled jobs/day
- No distributed worker pool needed yet (single Python process sufficient)
- APScheduler has persistent job state (SQLAlchemy backend) for recovery
- Can upgrade to Celery later without major refactoring (abstract task layer)

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|------------|------------|
| **httpx** | 0.27+ | HTTP client (AskNews API) | Async HTTP with connection pooling. Superior to requests for async code. Use with httpx.AsyncClient context manager. | HIGH |
| **python-dotenv** | 1.0+ | Environment config | Load .env files for API keys, DB connection strings. Standard for 12-factor apps. | HIGH |
| **Structlog** | 24.1+ | Structured logging | JSON logging for parsing in production. Better than built-in logging for time-series data context (timestamps, entity IDs). | MEDIUM |
| **Pytest** | 8.0+ | Testing framework | Standard Python testing tool. Use pytest-asyncio for async tests. | HIGH |
| **pytest-asyncio** | 0.24+ | Async test support | Essential for testing FastAPI routes and async database queries. | HIGH |
| **Coverage.py** | 7.4+ | Code coverage | Measure test coverage (target 80%+). | MEDIUM |
| **black** | 24.1+ | Code formatting | Standard formatter for Python projects. Zero-config, opinionated. | MEDIUM |
| **ruff** | 0.2+ | Linting | Modern, fast linter replacing flake8/isort/pylint. Replaces black+flake8 stack. | MEDIUM |

### Why NOT certain choices

| Technology | Why We Don't Use | Alternative |
|-----------|-----------------|------------|
| **TimescaleDB** | Premature optimization. PostgreSQL with proper indexing handles sentiment time-series well until 10M+ rows. TimescaleDB adds operational complexity (separate extension, learning curve, higher hosting costs). Use native PostgreSQL, migrate later if needed. | PostgreSQL with `created_at` indices and time-based partitioning (Phase 2) |
| **Celery** | Overkill for 2 simple recurring tasks. Requires message broker (Redis/RabbitMQ), worker processes, and operational overhead. APScheduler is lighter and sufficient at this scale. | APScheduler now, upgrade to Celery if you add 100+ tasks or distributed workers |
| **SQLModel** | Built on SQLAlchemy but thin wrapper. Less mature, smaller community. Adds complexity without benefit for this project. | SQLAlchemy 2.0 directly |
| **Tortoise ORM** | Less battle-tested at scale than SQLAlchemy. Smaller ecosystem, fewer integrations. Good for simple projects, but sentiment tracking needs robust ORM. | SQLAlchemy 2.0 |
| **Synchronous FastAPI** | Blocking I/O on each API call and database query. With AskNews calls + DB queries, would bottleneck. Async is essential. | Async FastAPI (all routes, all queries async) |
| **Django/DRF** | Heavyweight framework with built-in ORM. Better for traditional monolithic apps. FastAPI + SQLAlchemy is lighter, more modular, better for data pipelines. | FastAPI |
| **Scheduled Cron Jobs** | Hard to monitor, debug, and scale. No observability. Python-based scheduling (APScheduler) allows unified logging and error handling. | APScheduler |

## Stack Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (Vite + React + TypeScript)  [managed separately] │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API calls (httpx from Python side)
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI (Uvicorn)                          │
│  - Request validation (Pydantic)                            │
│  - Route handlers (async)                                  │
│  - OpenAPI docs auto-generated                             │
└────────┬────────────────────┬──────────────────┬────────────┘
         │                    │                  │
    ┌────▼────┐       ┌──────▼─────┐    ┌──────▼───────┐
    │ httpx   │       │SQLAlchemy  │    │ APScheduler  │
    │ Client  │       │ ORM async  │    │ (recurring   │
    │(AskNews)│       │ (asyncpg)  │    │  jobs)       │
    └────┬────┘       └──────┬─────┘    └──────┬───────┘
         │                   │                  │
         └───────────────────┴──────────────────┘
                     │
         ┌───────────▼──────────────┐
         │   PostgreSQL 16+         │
         │  (sentiment time-series) │
         └──────────────────────────┘
```

## Installation & Project Setup

### Core Dependencies

```bash
# Core FastAPI stack
pip install fastapi==0.115.0
pip install uvicorn[standard]==0.30.0
pip install pydantic==2.7.0

# Database
pip install sqlalchemy==2.0.35
pip install asyncpg==0.30.0
pip install alembic==1.14.0
pip install psycopg2-binary==2.9.9  # Also needed for non-async ops

# Data ingestion
pip install httpx==0.27.0
pip install asknews-python-sdk==0.4.0  # AskNews SDK

# Scheduling
pip install apscheduler==3.10.4

# Configuration & logging
pip install python-dotenv==1.0.0
pip install structlog==24.1.0

# Development & testing
pip install pytest==8.0.0
pip install pytest-asyncio==0.24.0
pip install pytest-cov==5.0.0
pip install black==24.1.1
pip install ruff==0.2.0
```

### Development Setup

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Fill in: DATABASE_URL, ASKNEWS_API_KEY, etc.

# Initialize database
alembic upgrade head

# Run tests
pytest --cov=app tests/

# Format code
black app/
ruff check app/

# Run development server
uvicorn app.main:app --reload
```

### Database Connection String

```python
# .env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/vibecheck_dev

# SQLAlchemy engine creation
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    os.getenv("DATABASE_URL"),
    echo=False,  # Set to True for SQL logging in development
    future=True,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
)
```

## Version Constraints & Compatibility

| Component | Min Version | Reason |
|-----------|------------|--------|
| Python | 3.11 | 3.10 works but lacks certain async optimizations |
| FastAPI | 0.115+ | Stable, recent fixes for async context handling |
| SQLAlchemy | 2.0+ | Required for async support via 2.0+ API |
| PostgreSQL | 14+ | 16+ recommended for JSON improvements |
| asyncpg | 0.29+ | Stability for production async queries |

## Deployment Considerations

### Production ASGI Server

```bash
# Use Gunicorn with Uvicorn workers for production
pip install gunicorn==21.2.0

# Run with multiple workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --access-logfile - \
  --error-logfile -
```

### Database Connection Pool

- SQLAlchemy pool_size=10, max_overflow=20 for ~50 concurrent requests
- Scale pool size proportionally: pool_size = (expected_concurrent_requests / 2)
- Use `pool_pre_ping=True` to verify stale connections in pool

### Environment Isolation

- Development: SQLite in-memory or local PostgreSQL with loose constraints
- Production: PostgreSQL 16+ with connection pooling, SSL enforcement
- Testing: Separate test database with truncation between test suites

## Migration from Alternatives

If you later need to switch:

| From | To | Effort | Reason |
|------|-----|--------|--------|
| APScheduler | Celery + Redis | Medium | Abstract task layer now, concrete implementation later |
| PostgreSQL | TimescaleDB | Low | Drop-in extension, same SQL dialect |
| SQLAlchemy | Tortoise ORM | High (not recommended) | Different ORM paradigm, would require rewrite |
| httpx | aiohttp | Low | Both async HTTP clients, similar APIs |

## High-Confidence Decisions

✓ **FastAPI + Uvicorn**: Industry standard for async Python APIs
✓ **SQLAlchemy 2.0 + asyncpg**: Mature, tested, best-in-class async ORM
✓ **PostgreSQL**: Proven time-series capabilities without TimescaleDB overhead
✓ **APScheduler**: Right-sized for 100 jobs/day, can upgrade later
✓ **Python 3.12**: Latest stable, excellent async/await performance

## Medium-Confidence Decisions

? **APScheduler over Celery**: True if you stay under 1000 jobs/day. Reassess if adding distributed processing
? **PostgreSQL over TimescaleDB**: True if aggregations stay under 100M rows. Reassess at scale
? **httpx over aiohttp**: Both solid; httpx slightly better DX, aiohttp slightly lighter

## Gaps & Phase 2 Candidates

- **Caching**: Redis for sentiment query caching (Phase 2)
- **Message queue**: RabbitMQ/Redis if adding WebSocket updates or distributed workers (Phase 2)
- **Monitoring**: Prometheus + Grafana for production metrics (Phase 2)
- **API rate limiting**: Use FastAPI middleware or external service (Phase 2)
- **Full-text search**: Elasticsearch if adding article search (Phase 2+)

## Sources

- FastAPI documentation: https://fastapi.tiangolo.com (knowledge cutoff Feb 2025)
- SQLAlchemy 2.0 migration guide: https://docs.sqlalchemy.org/en/20/ (2.0+ async stable)
- APScheduler docs: https://apscheduler.readthedocs.io (3.10+ recommended)
- asyncpg: https://magicstack.github.io/asyncpg (0.29+ production-ready)
- Uvicorn: https://www.uvicorn.org (0.29+ production-ready)

## Next Steps for Phase 1

1. Create FastAPI project structure (see ARCHITECTURE.md)
2. Set up PostgreSQL schema for articles, sentiment time-series, entities
3. Build AskNews API integration layer with httpx
4. Implement APScheduler jobs for 15-min news polling, hourly story polling
5. Create REST endpoints: sentiment history, entity comparison, trending entities
6. Write integration tests with pytest-asyncio

---

**Stack Summary:** Modern async Python (3.12) with FastAPI/SQLAlchemy/PostgreSQL, lightweight APScheduler for polling, zero unnecessary complexity. Right-sized for VibeCheck's data pipeline scale.
