# Research Summary: VibeCheck Backend Architecture & Implementation

**Project:** VibeCheck (Sentiment tracking dashboard for AI model/tool perception)
**Date:** February 2026
**Synthesized from:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Overall Confidence:** HIGH (stack decisions well-documented, architecture patterns proven, critical pitfalls identified)

---

## Executive Summary

VibeCheck is a **scheduled data pipeline backend** that polls an external API (AskNews) for sentiment data on AI entities, stores time-series data in PostgreSQL, and exposes it via REST endpoints for a React frontend. The recommended approach prioritizes **simplicity, reliability, and observability** over premature optimization.

**Core thesis:** Build a single-container, async Python backend (FastAPI + SQLAlchemy) with an in-process scheduler (APScheduler) for the MVP. This avoids the operational complexity of distributed systems while remaining scalable to 10K+ users. The main risk is not performance but **silent failures** in the scheduled pipeline—data collection, rate limiting, and schema design must be correct from day 1 because they're expensive to fix later.

**Key recommended technologies:**
- **FastAPI 0.115+** with Uvicorn for async HTTP handling
- **PostgreSQL 16+** with TimescaleDB-compatible schema design
- **SQLAlchemy 2.0+ with asyncpg** for async ORM
- **APScheduler 3.10+** for 15-min/hourly polling
- **Python 3.11+** for excellent async/await support

This stack is proven, well-documented, and has a clear upgrade path. The architecture separates API concerns (stateless request handling) from pipeline concerns (scheduled data ingestion), enabling independent scaling if needed.

---

## Key Findings

### From STACK.md: Technology Stack & Rationale

**High-confidence decisions (proven ecosystem):**
- **FastAPI 0.115+** over Django/Flask: Modern async-first framework, automatic OpenAPI docs, type-safe routes with Pydantic, significantly faster for data pipelines
- **SQLAlchemy 2.0+ with asyncpg**: Mature ORM with production-grade async support, fastest Python PostgreSQL driver (asyncpg 0.30+)
- **PostgreSQL 16+**: Handles time-series aggregations well with proper indexing; native JSON support for flexible metadata storage
- **APScheduler 3.10+** over Celery: Right-sized for 2 simple recurring tasks (15-min news, 60-min stories polling). Celery adds Redis/RabbitMQ broker, worker management, and operational overhead not justified at ~100 jobs/day
- **Python 3.11+**: Excellent async/await support; 3.12 recommended for performance improvements

**Explicitly avoided (with rationale):**
- **TimescaleDB:** Premature for MVP. Use native PostgreSQL with proper indexing until 10M+ rows. Migration to TimescaleDB is straightforward later (single ALTER TABLE)
- **Celery:** Overkill for 2 simple recurring tasks. APScheduler is lightweight and sufficient; can refactor to Celery in Phase 2 if tasks scale to 1000+/day
- **SQLModel:** Thin wrapper over SQLAlchemy with smaller ecosystem; direct SQLAlchemy 2.0 is cleaner
- **Synchronous FastAPI:** Blocking I/O on AskNews API calls and DB queries would bottleneck requests; async-first is essential

**Core dependencies (specific versions pinned):**
```
fastapi==0.115.0, uvicorn[standard]==0.30.0, pydantic==2.7.0
sqlalchemy==2.0.35, asyncpg==0.30.0, alembic==1.14.0
apscheduler==3.10.4, httpx==0.27.0
pytest==8.0.0, pytest-asyncio==0.24.0
```

**Confidence level:** HIGH (FastAPI/SQLAlchemy/PostgreSQL are proven patterns; APScheduler decision well-justified with clear upgrade path)

---

### From FEATURES.md: Product Scope & Phased Rollout

**Table stakes (MVP must-haves):**
1. Article-level sentiment ingestion from AskNews
2. Time-series aggregation (hourly/daily rollups)
3. Entity-specific sentiment endpoint (GET `/entities/{id}/sentiment?start=...&end=...`)
4. Scheduled polling (15-min news, 60-min stories) for predictable data freshness
5. Time-series storage with pre-computed aggregates (not computed on request)
6. Article deduplication (by external_id or content hash)
7. Separation of sentiment by source (news vs Reddit)
8. Entity lookup by name (for frontend autocomplete)
9. Historical data retention (6-12 months with explicit policy)

**Recommended MVP differentiator (low effort, high value):**
- **Entity comparison endpoint** (GET `/entities/compare?ids=claude,gpt4o&...`) — parallel sentiment arrays, enables side-by-side dashboard view

**MVP feature complexity assessment:**
- Article ingestion: 2-3 days (straightforward AskNews SDK use)
- Deduplication: 1 day (hash-based, simple logic)
- Time-series aggregation: 2-3 days (SQL design, needs testing at scale)
- Scheduled polling: 1-2 days (APScheduler configuration)
- Entity lookup: 1 day (simple table scan)
- Entity comparison: 1-2 days (parallel queries, response formatting)

**Defer to v2+ (unless users explicitly demand):**
- Trending entity detection (spike detection complexity unclear)
- Caching layer (add only if query latency >500ms)
- Sentiment velocity/momentum (requires 30+ days historical data)
- Real-time WebSocket updates (complexity unjustified for MVP)
- Full-text search (simple substring search sufficient)
- User accounts/personalization (single shared dashboard; defer account management)

**Anti-features (explicitly NOT building):**
- Own sentiment analysis model (use AskNews sentiment; custom NLP is v2+)
- Multi-source aggregation beyond AskNews (GitHub stars, Product Hunt are v2+)
- Predictive forecasting (show historical trends instead)
- Complex alerting system (defer to v2)

**Data freshness for v1:** Best-effort with monitoring (data usually fresh within 1 hour; acceptable gaps if ingestion fails). API responses include `last_article_ingested_at` so frontend knows data age.

**Confidence level:** HIGH (based on sentiment tracking backend patterns and industry norms)

---

### From ARCHITECTURE.md: System Design, Patterns & Build Order

**Recommended architecture: Layered design with separation of concerns**
```
FastAPI Routes (HTTP handlers, stateless)
         ↓
Service Layer (business logic, reusable)
         ↓
SQLAlchemy ORM (data access, models)
         ↓
PostgreSQL (single source of truth)
```

**Scheduler placement decision:**
- **Phase 1-2:** In-process with FastAPI (single container, one Python process, shared event loop)
  - Pros: Simplicity, no infrastructure overhead, fast startup
  - Cons: If API crashes, scheduler crashes; harder to scale scheduler independently
- **Phase 2+:** Separate process (Docker container running APScheduler Beat or Celery worker)
  - Trigger: When API latency is affected by long-running jobs, or when needing independent scaling

**Build order (dependency-aware):**
1. **Phase 1 (Week 1-2):** Foundation — Schema, ORM models, session management, .env config
2. **Phase 2 (Week 2-3):** API scaffold — FastAPI app, CORS, middleware, health check
3. **Phase 3 (Week 3):** AskNews integration — Client wrapper, error handling
4. **Phase 4 (Week 3-4):** Pipeline services — Ingestion logic, aggregation (manual testing only)
5. **Phase 5 (Week 4):** Scheduler integration — APScheduler setup, job registration
6. **Phase 6 (Week 4-5):** API endpoints — GET /entities, GET /entities/{id}/sentiment, etc.
7. **Phase 7 (Week 5+):** Optimization — Indexing, caching if needed, load testing

**Database schema highlights:**
- `entities`: Curated list (GPT-4o, Claude, Gemini, Cursor, v0)
- `articles`: Raw articles with external_id, sentiment, JSONB entities tagging
- `sentiment_timeseries`: Pre-aggregated by entity/timestamp with hourly/daily period column
- All timestamps in UTC (`TIMESTAMP WITH TIME ZONE`), no local time
- Indexes on `(entity_id, timestamp)` and `external_id` for deduplication

**Key architectural decisions:**

| Decision | Choice | Why |
|----------|--------|-----|
| **Scheduler location** | Same FastAPI process (Phase 1) | Simplicity for MVP; separate container in Phase 2 if needed |
| **Async pattern** | APScheduler + AsyncIOScheduler | Native async support, minimal overhead |
| **Job idempotency** | Check `external_id` before insert | Safely handles re-runs without duplicates |
| **Transaction scope** | Per-job atomic | Prevents partial writes (article inserted but sentiment fails) |
| **Aggregation** | Pre-compute hourly/daily in separate table | Avoids expensive runtime aggregations |
| **Schema design** | Explicit `period` column | Enables future TimescaleDB migration without code changes |

**Confidence level:** HIGH (patterns are standard in FastAPI ecosystem; build order is dependency-aware and realistic)

---

### From PITFALLS.md: Critical Risks & Mitigation (Phase-Specific)

**Critical pitfalls (must mitigate in Phase 1):**

#### Pitfall 1: API Cost Overruns from Edge Cases
- **Risk:** Retry storms, clock skew, broad entity filtering → 2-3x budget consumed unexpectedly
- **Mitigation:**
  - Hard cap API calls (e.g., 5000/day with alerts at 3000)
  - Exponential backoff: max 3 retries with delays (1s, 4s, 16s), never retry 4xx errors
  - Deduplicate: check `last_poll_time` per entity, skip if polled in last 15 mins
  - Use APScheduler with `max_instances=1`, `misfire_grace_time=60` to prevent concurrent runs
  - Test in sandbox, never against production API during development
- **Detection:** Monthly bill spike, 429 errors in logs, duplicate records

#### Pitfall 2: PostgreSQL Time-Series Schema Collapses at Scale
- **Risk:** Naive schema (single table, UNIQUE URL constraint) → insert performance degrades 100ms→5s+ at 10K records
- **CRITICAL MITIGATION:** **Use TimescaleDB from day 1** (or design schema with TimescaleDB compatibility)
  - Create hypertable with auto-partitioning and 90-day retention policy
  - Separate tables for hourly/daily aggregates (don't query raw articles for trends)
  - Remove UNIQUE constraints; check duplicates in application logic
  - Batch inserts: collect 100 records, INSERT with multi-row VALUES syntax
  - All timestamps in UTC
- **Alternative (if avoiding TimescaleDB):** Design schema to enable migration with single ALTER TABLE statement later
- **Detection:** Insert slowdown, aggregation queries taking >5 seconds, backup bloat

#### Pitfall 3: Scheduler Reliability — Silent Task Failures
- **Risk:** Job fails, no alert. Data collection stops. Discovered weeks later by customer
- **Mitigation:**
  - Health check endpoint that verifies when each job last ran
  - Alert if job hasn't run in expected window (>30 mins for 15-min job)
  - Log every job start/completion with unique execution ID
  - Store execution log in database for audit trail
  - Database-level lock to prevent concurrent runs: `SELECT ... FOR UPDATE SKIP LOCKED`
  - **Phase 2+:** Migrate to Celery with persistent broker if reliability becomes critical
- **Detection:** Data gaps, duplicate articles, no logs from scheduled jobs

#### Pitfall 4: Entity Name Variation Explosion
- **Risk:** "Claude" appears as "Claude 3", "Anthropic Claude", etc. → data fragments across variations, analytics wrong
- **Mitigation:**
  - Define ENTITY_VARIATIONS dict with canonical names and variations upfront
  - Normalize at insertion time (not in UI)
  - Store both extracted and canonical names (for auditing)
  - Quarterly audit: find unmapped entity names, update rules
  - Test normalization against real AskNews data before production
- **Detection:** Same article under multiple names, sentiment averages wildly inconsistent

#### Pitfall 5: Monorepo Python + JavaScript Conflicts
- **Risk:** npm install affects Python tooling, conflicting setup instructions, CI build order wrong
- **Mitigation:**
  - Explicit directory structure: `frontend/` and `backend/` fully isolated
  - Separate package managers (npm for frontend, pip for backend)
  - Docker Compose for local development (eliminates "works on my machine")
  - Unified Makefile with test, lint, format commands
  - Root README documents monorepo structure and setup
- **Detection:** Developer confusion about setup, path issues in deployed app

**Moderate pitfalls (Phase 1-2):**
- **Lack of observability:** Add structured logging (Structlog) with entity, duration, request ID fields from day 1
- **Database testing issues:** Use fixtures for setup/teardown, mock external API calls
- **Timezone bugs:** All timestamps in UTC, convert to user timezone only in responses
- **Rate limit headers ignored:** Parse `X-RateLimit-Remaining` and back off if needed

**Phase-specific warnings:**

| Phase | Pitfall | Mitigation | Why Phase 1 |
|-------|---------|-----------|----------|
| **Phase 1** | Schema design | TimescaleDB-compatible or actual TimescaleDB | Changing schema later is expensive |
| **Phase 1** | Scheduler health | Health check endpoint + execution logging | Silent failures are hard to debug |
| **Phase 1** | API cost control | Hard cap + budget tracking | Budget overruns happen fast |
| **Phase 1** | Entity mapping | Validate normalization against real data | Fragmented data is irreversible |
| **Phase 1** | Monorepo structure | Clear boundaries, Docker Compose | Foundation matters for team velocity |
| **Phase 2** | Aggregation bugs | Test against known data, explicit time bounds | Bugs compound over months of data |
| **Phase 2** | Testing | Fixtures and mocks, not real DB | Tests must pass in CI |

**Confidence level:** MEDIUM-HIGH (pitfalls are recognized patterns; mitigations are actionable; AskNews specifics need validation in Phase 1)

---

## Implications for Roadmap

### Recommended Phase Structure (4-5 Weeks MVP)

**Phase 1: Foundation (Weeks 1-2)**
- **Deliverable:** Skeleton backend that reliably injects, deduplicates, and stores data
- **Includes:**
  - Database schema (entities, articles, sentiment_timeseries) with TimescaleDB-compatible design
  - SQLAlchemy ORM models with proper constraints
  - FastAPI app scaffold with health endpoint
  - AskNewsClient wrapper (fetch_news, fetch_stories, error handling)
  - NewsIngestionService and StoryIngestionService (manual testing only, no scheduler)
  - API budget tracking and exponential backoff retry
  - Entity normalization rules (ENTITY_VARIATIONS dict) with validation
  - Structured logging setup (Structlog)
  - Docker Compose for local development
- **Features enabled:** Article ingestion, deduplication, source tagging, entity normalization
- **Pitfalls prevented:** API cost overruns, schema collapse, entity fragmentation, monorepo friction
- **Success criteria:**
  - Ingest 100+ articles without duplicates
  - No API calls exceed budget cap
  - Data stored correctly in PostgreSQL
  - Logs are structured and searchable
  - Entity normalization covers >95% of test articles

**Phase 2: Scheduler & Core Backend (Weeks 2-3)**
- **Deliverable:** Fully functional data pipeline with scheduled polling and aggregation
- **Includes:**
  - APScheduler integration (15-min news job, 60-min stories job)
  - Job state tracking (last_run timestamp, execution status)
  - Health check endpoint (verifies scheduler is running)
  - Execution audit log table
  - Database-level locks to prevent concurrent runs
  - Time-series aggregation (hourly/daily rollups)
  - Comprehensive integration tests (pytest-asyncio with fixtures, not real DB)
  - Entity comparison endpoint
- **Features enabled:** Scheduled polling, sentiment aggregation, comparison queries
- **Pitfalls prevented:** Scheduler silent failures, aggregation bugs, testing tightly coupled to DB
- **Success criteria:**
  - Scheduler runs every 15/60 mins without duplicate data
  - Health check accurately reports scheduler status
  - Aggregation queries return correct averages (test with known data)
  - Tests pass in CI without requiring real PostgreSQL

**Phase 3: API Endpoints & Frontend Integration (Weeks 3-4)**
- **Deliverable:** Complete REST API for frontend consumption
- **Includes:**
  - GET /entities (list all, latest sentiment)
  - GET /entities/{id}/sentiment (time-series with optional date range)
  - GET /entities/compare (side-by-side comparison)
  - GET /entities/search (autocomplete)
  - GET /articles (recent articles by entity, paginated)
  - Error handling (400, 404, 500 with meaningful messages)
  - CORS middleware
  - OpenAPI docs (auto-generated)
- **Features enabled:** Dashboard-ready API with entity queries and comparisons
- **Pitfalls prevented:** Slow aggregation queries, timezone confusion, stale cache
- **Success criteria:**
  - All endpoints return <500ms p95 latency
  - Frontend can render sentiment charts
  - OpenAPI docs are accurate

**Phase 4: Optimization & Monitoring (Week 4+)**
- **Deliverable:** Production-ready monitoring and performance tuning
- **Includes:**
  - Query optimization (EXPLAIN ANALYZE, strategic indexing)
  - Redis caching if query latency >500ms
  - Prometheus metrics and alerting
  - Load testing (concurrent users)
  - Backup/restore procedures
- **Success criteria:**
  - p95 latency <200ms under load
  - No data gaps >30 mins
  - Alerts fire before issues escalate

---

## Research Gaps & Validation Needed

### Needs Research During Planning

**Phase 1 (block on these):**
- [ ] **AskNews entity extraction accuracy:** Test fetch against real API. What % of articles match our entity list? Adjust normalization rules based on real data
- [ ] **Exact rate limit behavior:** Confirm X-RateLimit-Remaining and X-RateLimit-Reset header behavior. Test against production API (with permission)
- [ ] **TimescaleDB vs native PostgreSQL:** Revisit decision. Recommend: Design for TimescaleDB compatibility but don't require extension until performance issue confirmed

**Phase 2 (validate during Phase 1):**
- [ ] **Aggregation query performance:** Test with 100K, 1M, 10M articles. Determine if indexes suffice or TimescaleDB migration needed
- [ ] **Scheduler persistence:** Verify APScheduler SQLAlchemy job store works reliably with asyncpg
- [ ] **Async pattern safety:** Confirm no blocking I/O in routes or jobs

**Phase 3 (after Phase 2):**
- [ ] **Frontend data patterns:** What queries will frontend make? Determine caching strategy

### Patterns Well-Documented (No Additional Research Needed)

- ✓ **FastAPI architecture:** Industry standard, extensive docs, proven patterns
- ✓ **SQLAlchemy 2.0 async:** Mature, clear examples in official docs
- ✓ **PostgreSQL time-series:** Best practices established (with or without TimescaleDB)
- ✓ **APScheduler vs Celery tradeoff:** Well-documented in STACK.md
- ✓ **Monorepo structure:** Docker Compose patterns proven

---

## Confidence Assessment

| Area | Confidence | Rationale | Gaps |
|------|-----------|-----------|------|
| **Stack** | HIGH | FastAPI, SQLAlchemy, PostgreSQL mature; versions pinned; APScheduler decision justified | AskNews SDK specifics untested |
| **Features** | HIGH | Feature breakdown comprehensive; MVP scope realistic (4-5 weeks); clear defer list | Frontend data patterns unknown until Phase 3 |
| **Architecture** | HIGH | Layered pattern standard; build order dependency-aware; schema sound | Scheduler persistence needs Phase 1 validation |
| **Pitfalls** | MEDIUM-HIGH | Pitfalls are recognized patterns; mitigations detailed and actionable | AskNews rate limit behavior not verified |
| **Phase Estimates** | MEDIUM | 4-5 weeks for MVP realistic if team familiar with async Python; may slip if not | Developer experience with async unknown |

**Key uncertainties:**
1. AskNews API rate limit behavior (not verified against current API)
2. Team experience with async Python (could impact Phase 1 timeline)
3. PostgreSQL query performance at scale (will determine if TimescaleDB needed)
4. Actual ingestion rate and query patterns (will inform Phase 3-4 optimization)

---

## How This Informs Roadmap

**For Roadmapper:**

**Phase 1 is NOT optional — it's the foundation:**
- Schema design must be right (TimescaleDB-compatible or actual TimescaleDB)
- Scheduler must be monitored (health checks, execution logs)
- Entity mapping must be validated (against real AskNews data)
- Monorepo structure must be clear (Docker Compose, isolated directories)

**Features should cluster by dependency:**
- Ingest + deduplication + source tagging (Phase 1)
- Aggregation + comparison (Phase 2)
- Full API + frontend integration (Phase 3)
- Optimization + monitoring (Phase 4)

**Risks to highlight in roadmap:**
- Schema migration is expensive (get it right in Phase 1)
- Silent failures in scheduler are costly (add health checks early)
- Entity fragmentation is irreversible (validate mapping before production)
- Monorepo friction affects team velocity (structure it correctly from day 1)

**Upgrade paths:**
- APScheduler → Celery (Phase 2-3 if task count grows)
- PostgreSQL → TimescaleDB (Phase 2-3 if aggregation queries slow)
- In-process scheduler → Separate container (Phase 2 if API latency issues)
- No cache → Redis (Phase 3 if query latency >500ms)

---

## Summary: What to Build When

**Week 1-2 (Phase 1):**
Schema → Models → Services (manual test) → Docker Compose

**Week 2-3 (Phase 2):**
Scheduler → Health checks → Aggregation → Tests

**Week 3-4 (Phase 3):**
API endpoints → CORS → OpenAPI → Frontend integration

**Week 4+ (Phase 4):**
Optimization → Monitoring → Load testing

---

## Sources & Confidence

**High confidence (proven patterns):**
- FastAPI documentation: https://fastapi.tiangolo.com
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20
- asyncpg: https://magicstack.github.io/asyncpg
- PostgreSQL: https://www.postgresql.org/docs

**Medium confidence (ecosystem knowledge + industry patterns):**
- APScheduler vs Celery tradeoff (confirmed in STACK.md, aligns with 2025 ecosystem)
- PostgreSQL time-series design (industry consensus; TimescaleDB standard)
- Async Python patterns (standard in 2024-2025)
- Monorepo best practices (proven patterns)
- Domain pitfalls (pattern recognition from industry experience)

**Low confidence (needs Phase 1 validation):**
- AskNews API rate limit behavior (no access to official docs)
- PostgreSQL query performance at scale (schema-dependent)
- Team experience with async Python (unknown variable)

---

**Ready for Roadmap:** VibeCheck backend has well-scoped phases, proven technology choices, identified risks with mitigations, and a clear upgrade path. Recommend proceeding to requirements definition with Phase 1 focus on reliable data ingestion and storage.
