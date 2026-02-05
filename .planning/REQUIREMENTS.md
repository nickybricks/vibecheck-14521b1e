# Requirements: VibeCheck

**Defined:** 2026-02-05
**Core Value:** Users can see how sentiment around AI models and tools has changed over time, with clear time-series data powered by real news and Reddit community opinion.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Data Ingestion

- [ ] **INGT-01**: System fetches news articles from AskNews `/news` endpoint with entity-specific `string_guarantee` filters
- [ ] **INGT-02**: System fetches story clusters from AskNews `/stories` endpoint with sentiment time-series and Reddit data
- [ ] **INGT-03**: System normalizes entity name variations (e.g., "GPT-4o", "GPT 4o", "ChatGPT") to canonical names at ingestion time

### Storage

- [x] **STOR-01**: System stores raw article metadata (title, URL, source, published date, sentiment score) in PostgreSQL
- [x] **STOR-02**: System stores pre-computed hourly and daily sentiment aggregates per entity in a time-series table

### Scheduling

- [ ] **SCHD-01**: System polls AskNews `/news` every 15 minutes via APScheduler
- [ ] **SCHD-02**: System polls AskNews `/stories` every 60 minutes via APScheduler
- [ ] **SCHD-03**: System logs each job execution with status, duration, and error details

### API

- [ ] **API-01**: GET `/entities` returns all tracked AI tools/models with their latest sentiment scores
- [ ] **API-02**: GET `/entities/{id}/sentiment` returns time-series sentiment data with optional date range filter

### Infrastructure

- [x] **INFR-01**: Docker Compose configuration for local development with FastAPI + PostgreSQL containers
- [ ] **INFR-02**: CORS middleware configured to allow React frontend requests

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Data Quality

- **DEDUP-01**: Article deduplication via external_id or content hash
- **BUDG-01**: Hard cap on API calls with budget tracking and alerts

### Sentiment Detail

- **SENT-01**: Separate tracking of news vs Reddit sentiment per entity

### API Enhancements

- **API-03**: GET `/entities/compare` for side-by-side sentiment comparison
- **API-04**: GET `/articles` for paginated article list by entity

### Infrastructure Enhancements

- **HLTH-01**: Health check endpoint reporting scheduler status and last job run times
- **MIGR-01**: Alembic database migrations for version-controlled schema changes
- **LOG-01**: Structured logging with entity, duration, request ID fields

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Frontend UI development | Colleague handles this |
| Own NLP/sentiment analysis | AskNews provides built-in sentiment |
| Real-time WebSocket updates | REST sufficient for v1 |
| Financial analytics endpoint | Not needed for tool sentiment tracking |
| Alert/notification system | Defer to v2 |
| Sentiment forecasting/ML | Defer to v2+ |
| Additional data sources (GitHub, Product Hunt, X) | Defer to v2+ |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STOR-01 | Phase 1 | Complete |
| STOR-02 | Phase 1 | Complete |
| INFR-01 | Phase 1 | Complete |
| INGT-01 | Phase 2 | Pending |
| INGT-02 | Phase 2 | Pending |
| INGT-03 | Phase 2 | Pending |
| SCHD-01 | Phase 2 | Pending |
| SCHD-02 | Phase 2 | Pending |
| SCHD-03 | Phase 2 | Pending |
| API-01 | Phase 3 | Pending |
| API-02 | Phase 3 | Pending |
| INFR-02 | Phase 3 | Pending |

**Coverage:**
- v1 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0

---
*Requirements defined: 2026-02-05*
*Last updated: 2026-02-05 after Phase 1 completion*
