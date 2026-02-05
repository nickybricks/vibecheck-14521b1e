# Roadmap: VibeCheck

## Overview

VibeCheck's backend journey follows a build-validate-expose pattern: establish reliable storage and foundation (Phase 1), implement scheduled data ingestion from AskNews with entity normalization (Phase 2), then serve time-series sentiment data to the frontend via REST API (Phase 3). This roadmap delivers a production-ready Python backend that tracks AI model/tool sentiment over time.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Storage** - Database schema, ORM models, Docker environment
- [ ] **Phase 2: Data Pipeline** - AskNews integration, scheduled ingestion, entity normalization
- [ ] **Phase 3: API & Integration** - REST endpoints, CORS middleware, frontend-ready API

## Phase Details

### Phase 1: Foundation & Storage
**Goal**: Backend can reliably store article metadata and pre-computed sentiment aggregates
**Depends on**: Nothing (first phase)
**Requirements**: STOR-01, STOR-02, INFR-01
**Success Criteria** (what must be TRUE):
  1. PostgreSQL database runs locally with proper schema for articles and time-series sentiment
  2. SQLAlchemy models exist for entities, articles, and sentiment aggregates
  3. Docker Compose successfully starts FastAPI and PostgreSQL containers
  4. Database schema supports TimescaleDB-compatible time-series patterns (indexed by entity_id, timestamp)
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Docker Compose environment and backend Python project structure (completed 2026-02-05)
- [x] 01-02-PLAN.md — SQLAlchemy async ORM models and Alembic migrations (completed 2026-02-05)
- [x] 01-03-PLAN.md — FastAPI application with health endpoint and stack verification (completed 2026-02-05)

### Phase 2: Data Pipeline
**Goal**: Backend continuously fetches news and stories from AskNews with normalized entity tracking
**Depends on**: Phase 1
**Requirements**: INGT-01, INGT-02, INGT-03, SCHD-01, SCHD-02, SCHD-03
**Success Criteria** (what must be TRUE):
  1. System fetches articles from AskNews `/news` endpoint with entity filters every 15 minutes
  2. System fetches story clusters from AskNews `/stories` endpoint every 60 minutes
  3. Entity name variations (e.g., "GPT-4o" vs "GPT 4o") normalize to canonical names at ingestion
  4. Scheduler logs each job execution with status, duration, and errors
  5. No duplicate articles appear in database (deduplication works)
**Plans**: 4 plans

Plans:
- [x] 02-01-PLAN.md — AskNews SDK integration and entity normalization service (completed 2026-02-05)
- [x] 02-02-PLAN.md — News ingestion job with deduplication and retry logic (completed 2026-02-05)
- [x] 02-03-PLAN.md — Story ingestion job with Reddit sentiment extraction (completed 2026-02-05)
- [x] 02-04-PLAN.md — APScheduler integration with health monitoring (completed 2026-02-05)

### Phase 3: API & Integration
**Goal**: Frontend can query entity sentiment data via REST endpoints
**Depends on**: Phase 2
**Requirements**: API-01, API-02, INFR-02
**Success Criteria** (what must be TRUE):
  1. GET `/entities` returns all tracked AI tools/models with latest sentiment scores
  2. GET `/entities/{id}/sentiment` returns time-series sentiment data with optional date filtering
  3. React frontend can successfully fetch data from FastAPI backend (CORS configured)
  4. API responds with proper error codes (400, 404, 500) and meaningful messages
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — Entity endpoints and Pydantic schemas (created 2026-02-05)
- [ ] 03-02-PLAN.md — Sentiment time-series endpoints with pagination (created 2026-02-05)
- [ ] 03-03-PLAN.md — CORS middleware configuration for frontend integration (created 2026-02-05)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Storage | 3/3 | Complete | 2026-02-05 |
| 2. Data Pipeline | 4/4 | Complete (not yet verified) | 2026-02-05 |
| 3. API & Integration | 0/3 | Planned (ready for execution) | - |

---
*Roadmap created: 2026-02-05*
*Last updated: 2026-02-05 (Phase 3 planned)*
