# VibeCheck

## What This Is

A backend data pipeline and API that tracks public sentiment around popular AI models and tools over time. It uses the AskNews API (hybrid: News Search with Entity Filters + Story Clustering) to ingest news articles and Reddit threads, processes sentiment data, and stores time-series results in PostgreSQL. A colleague builds the React frontend; this project covers the Python backend and data layer.

## Core Value

Users can see how sentiment around AI models and tools has changed over time, with clear time-series data powered by real news and Reddit community opinion.

## Requirements

### Validated

- ✓ Vite + React + TypeScript frontend scaffold — existing
- ✓ shadcn/ui component library — existing
- ✓ Vitest testing setup — existing

### Active

- [ ] AskNews API integration with Python SDK (OAuth2 auth)
- [ ] Hybrid data ingestion: `/news` endpoint with entity filters + `/stories` endpoint for narrative clustering
- [ ] Fixed curated entity list (AI models: GPT-4o, Claude, Gemini, Llama, Mistral; AI tools: Cursor, Lovable, v0, GitHub Copilot, Replit)
- [ ] Scheduled polling jobs (news every 15 min, stories hourly)
- [ ] PostgreSQL storage for articles, sentiment time-series, story clusters, and Reddit threads
- [ ] Sentiment aggregation: daily/hourly averages per entity, separate news vs Reddit sentiment
- [ ] FastAPI backend serving REST endpoints for the frontend
- [ ] API endpoints: entity sentiment history, entity comparison, trending entities, article details

### Out of Scope

- Frontend UI development — colleague handles this
- Own NLP/sentiment analysis — AskNews provides built-in sentiment at article and story level
- Real-time WebSocket updates — REST is sufficient for v1
- Financial analytics endpoint — not needed for v1 tracking
- Deep news agentic research — overkill for scheduled tracking
- Knowledge graph queries — defer to future iteration
- Alert/notification system — defer to v2
- Sentiment forecasting/ML — defer to v2
- Additional data sources (GitHub, Product Hunt, X API) — defer to v2

## Context

- **AskNews API**: Processes 300k+ articles daily, 50k+ sources, 13 languages. Provides built-in sentiment analysis, entity extraction (GLiNER), and story clustering with time-series sentiment. Reddit sentiment included in story responses.
- **Key endpoints**: `/news` (1 request, <100ms, entity filters via `string_guarantee`) and `/stories` (10 requests, ~500ms, time-series sentiment + Reddit)
- **Sentiment data**: Article-level sentiment score (-1 to +1), story-level time-series sentiment, Reddit-specific sentiment per thread
- **Python SDK**: `asknews-python-sdk` with OAuth2 client credentials auth
- **Pricing**: Spelunker tier ($250/mo, 1,500 base requests) for dev. With 10 entities at 15-min intervals + hourly stories, expect ~4,000-5,000 requests/month in production.
- **Existing codebase**: Vite/React/TypeScript scaffold with shadcn/ui, Vitest, Tailwind. Backend is greenfield — Python/FastAPI to be added alongside existing frontend.

## Constraints

- **Tech stack (backend)**: Python with FastAPI — strong ecosystem for data work and AskNews SDK
- **Tech stack (frontend)**: Vite + React + TypeScript — already scaffolded, colleague manages
- **Database**: PostgreSQL — good for time-series queries, production-ready
- **API budget**: Start with Spelunker tier during development to keep costs low
- **Model profile**: Budget — use cost-efficient models for GSD agents
- **Scope**: Backend and data only — no frontend work in this project cycle

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid AskNews approach (News Search + Story Clustering) | News search gives high-precision entity tracking at low cost; story clustering provides narrative tracking with Reddit sentiment | -- Pending |
| Use AskNews built-in sentiment (no own NLP) | AskNews provides article-level and story-level sentiment out of the box, including Reddit | -- Pending |
| Fixed curated entity list | Simpler implementation, controlled API costs, consistent tracking | -- Pending |
| PostgreSQL for storage | Reliable for time-series sentiment data, good query support, production-ready | -- Pending |
| FastAPI for backend | Python ecosystem, async support, automatic OpenAPI docs, works well with AskNews SDK | -- Pending |
| Scheduled polling (not on-demand) | Consistent data collection, predictable API costs, no cold-start latency for users | -- Pending |

---
*Last updated: 2026-02-05 after initialization*
