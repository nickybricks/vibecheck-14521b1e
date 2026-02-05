# Feature Landscape: Sentiment Tracking Backend

**Domain:** Sentiment tracking and news intelligence pipeline
**Project:** VibeCheck (AI model/tool sentiment dashboard)
**Researched:** 2026-02-05
**Confidence:** HIGH (based on domain patterns in sentiment tracking, news aggregation, and time-series analytics backends)

## Table Stakes

Features users expect. Missing any of these = product feels incomplete or fails its core promise.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| **Ingest article-level sentiment** | Core of product: without sentiment on each article, can't track "how people feel about GPT-4o" | Low | AskNews API integration | Article-level sentiment (-1 to +1) from AskNews, stored with article record |
| **Aggregate sentiment over time** | Users want to see "has GPT-4o sentiment improved this month?" — raw articles aren't actionable | Medium | Article ingestion, DB schema | Hourly/daily rollups (avg, stddev, count) per entity, queryable by time range |
| **Entity-specific sentiment endpoint** | Frontend needs: "give me GPT-4o sentiment for last 30 days" | Low | Aggregation pipeline, REST design | GET `/entities/{entity_id}/sentiment?start_date=&end_date=` |
| **Scheduled polling (not on-demand)** | Ensures consistent daily/hourly snapshots, predictable API costs, no latency surprises for users | Medium | Task scheduling (APScheduler), job state tracking | Cron-like jobs: news every 15 min, stories hourly; idempotent by design |
| **Sentiment time-series storage** | Can't compute aggregates on-the-fly for 30-day spans; need pre-computed hourly/daily snapshots | Medium | PostgreSQL schema, aggregation logic | Separate table: entity_id, timestamp, sentiment_avg, sentiment_stddev, source_count, sentiment_source |
| **Article deduplication** | AskNews may return same article twice; duplicates skew sentiment counts and waste API budget | Medium | Hashing/URL normalization, duplicate detection logic | Content hash or URL canonical form; skip articles with same hash |
| **Separation of news vs Reddit sentiment** | Different audiences have different sentiment; users want to see "news says GPT-4o +0.7, Reddit says +0.3" | Medium | Source tagging in data model, separate aggregation | Track sentiment_source (news, reddit, etc.) in time-series table |
| **Entity lookup by name** | Frontend autocomplete: "find me Claude, GPT-4o, Cursor, etc." | Low | Entity table with name/slug/aliases | GET `/entities` or GET `/entities/search?q=claude` |
| **Historical data retention** | Users want 6-month or 1-year sentiment trends; can't recompute from articles if articles are deleted | Medium | Retention policy, archival strategy | Keep last 6-12 months of time-series; articles can be pruned (aggregates remain) |
| **API documentation** | Backend is useless if frontend dev can't figure out endpoints | Low | OpenAPI (automatic with FastAPI), README | FastAPI auto-generates OpenAPI docs; should document schema, date formats, aggregation logic |
| **Basic error handling** | API should not 500 on bad input; should return meaningful errors | Low | FastAPI validation, proper HTTP status codes | 400 for bad query (e.g., invalid date), 404 for missing entity, 500 only if server fails |
| **Database persistence** | Data is lost on server restart if no persistence | Low | PostgreSQL setup, connection pooling | PostgreSQL backend; use SQLAlchemy with connection pooling for reliability |

## Differentiators

Features that set product apart. Not expected, but valuable for competitive advantage or user retention.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Entity comparison endpoint** | Frontend can show: "How does Claude sentiment compare to GPT-4o?" — side-by-side time-series | Medium | API design, frontend integration | GET `/entities/compare?ids=claude,gpt4o&start=&end=` returns parallel sentiment arrays |
| **Trending entities detection** | Show "which AI models are people talking about most right now?" — captures emerging interest | Medium | Trending calculation (spike detection or volume-based), caching | Identify entities with sentiment spikes or volume increases in last 24-48h; cache results |
| **Sentiment velocity/momentum** | Not just sentiment level but "is sentiment trending up or down?" — shows trajectory | Medium | Time-series math (linear regression, moving averages), calculation on read | Calculate slope of sentiment over last 7/30 days; return as "trending_direction": "up" |
| **Source-level attribution** | Show "this positive spike came from these 5 articles" — users understand *why* sentiment changed | High | Granular source tracking, ranking logic | Link top articles to each time-series bucket; rank by sentiment impact |
| **Custom date range flexibility** | Users can query "last 90 days" or "Feb 1-7" or "specific time period" without preset buckets | Low | Flexible query parsing, query optimization | Support start_date/end_date parameters; handle DST, leap seconds, timezone awareness |
| **Sentiment by source type** | Break down "is positive sentiment from news or Reddit?" — reveals community vs media perception | Medium | Source type tagging (news, reddit, hackernews, twitter, etc.), separate aggregation | Extend data model to track source_type; return separate sentiment scores per type |
| **Real-time article ingestion view** | Show "12 new articles about Claude in the last hour" — transparency into data freshness | Medium | Live article feed endpoint, caching | GET `/feed?entity=claude&limit=20` returns newest articles; good for debugging data gaps |
| **Multi-entity batch query** | Frontend wants sentiment for 10 entities at once (not 10 separate requests) | Low | Bulk query endpoint, query optimization | GET `/entities/batch?ids=claude,gpt4o,gemini` returns all sentiment in one request |
| **Aggregation mode flexibility** | Let frontend choose: "give me daily or hourly or weekly aggregates" — not hardcoded to daily | Medium | Store multiple aggregation levels, query parameter for granularity | Compute and store hourly, daily, weekly; client chooses via granularity parameter |
| **Caching layer for common queries** | 100 requests/day for "last 30 days of Claude sentiment" — shouldn't recompute each time | High | Redis or in-memory cache, cache invalidation strategy | Cache popular queries (entity sentiment, comparisons) for 5-15 min; invalidate on new aggregation |
| **Webhook/callback for new data** | Frontend can be notified when new sentiment arrives instead of polling | High | Webhook infrastructure, delivery guarantees, retry logic | Notify on new aggregates; requires frontend URL registration; defer to v2 |

## Anti-Features

Features to explicitly NOT build. Common mistakes in sentiment tracking and news pipelines.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Real-time streaming sentiment** | Adds complexity (WebSocket, message queues, event sourcing) far beyond MVP value; 15-min polling suffices | Accept eventual consistency; scheduled polling is fine for historical tracking |
| **Own sentiment analysis model** | AskNews provides sentiment; building own NLP model adds weeks of work, training data curation, model drift — not core to VibeCheck | Use AskNews built-in sentiment scores; if dissatisfied, swap sentiment provider later |
| **Multi-source aggregation (v1)** | Temptation to add GitHub stars, Product Hunt, Twitter, HackerNews, etc. — balloons API cost and integration effort | Stick to AskNews (news + Reddit) via hybrid approach; other sources are v2 work |
| **Predictive sentiment forecasting** | ML models for "Claude sentiment will be +0.8 next week" — not part of MVP; requires historical data and validation | Show historical trends (velocity) instead; forecasting is v2 if users ask |
| **User accounts / personalization** | "Let users customize which entities they track" — adds auth, user tables, permission checks; not needed for shared dashboard | Single shared sentiment dashboard; personalization is v2 |
| **Complex alert system** | "Email me when Claude sentiment drops below 0.5" — adds notification infrastructure, user preferences, alert fatigue — defer | Defer to v2; for now, dashboard is always-on |
| **On-demand sentiment analysis** | "I give you a URL, you sentiment-analyze it" — shifts product from dashboard to API service; out of scope | Stay focused on scheduled, entity-specific tracking |
| **Full-text search on articles** | "Find all articles mentioning GPT-4o that are negative" — adds search index, query complexity | Store article title/summary; if needed, simple substring search; full-text search is v2 |
| **Entity relationship graph** | "Show how Claude and GPT-4o sentiment are correlated" — graph data structure, correlation math, visualization complexity | Defer correlation analysis to v2; for now, entity sentiments are independent tracks |
| **Sentiment explanation/reasoning** | "This article is +0.7 because..." — requires extracting/summarizing key phrases; adds NLP pipeline | Use article title/summary from AskNews; don't engineer explanations |
| **Manual sentiment correction UI** | "Adjust article sentiment if AskNews got it wrong" — introduces human bias, audit trails, conflict resolution | Trust AskNews sentiment as ground truth; if systematically wrong, swap provider |
| **Time-series interpolation** | "Fill gaps in sentiment data on missing days with interpolated values" — introduces false precision | Show only actual data; gaps are honest if ingestion fails |
| **Infinite historical storage** | "Keep all articles forever" — balloons database size, slows queries | Retention policy: keep articles 6-12 months; sentiment aggregates longer |
| **Heavy pre-aggregation burden** | "Pre-compute all possible time windows/breakdowns" — exponential storage, unclear what's useful | Compute hourly/daily/weekly only; other granularities on-demand |

## Feature Dependencies

```
Article Ingestion (news/reddit from AskNews)
    ↓
    ├─→ Article Deduplication
    ├─→ Source Type Tagging
    └─→ Sentiment Extraction (from AskNews)
            ↓
            └─→ Time-Series Aggregation (hourly/daily rollups)
                    ↓
                    └─→ Entity Sentiment Endpoint (GET /entities/{id}/sentiment)
                            ↓
                            ├─→ Entity Comparison Endpoint (depends on aggregation working for multiple entities)
                            ├─→ Trending Detection (depends on aggregation + time-series math)
                            ├─→ Sentiment Velocity (depends on multi-point time-series)
                            └─→ Source Attribution (depends on granular article tracking)

Scheduled Polling Job Orchestration
    ↓
    ├─→ News Poll (every 15 min via AskNews /news endpoint)
    └─→ Stories Poll (every 60 min via AskNews /stories endpoint)
            ↓
            └─→ Job State Tracking (idempotency, error recovery)

Entity Management
    ↓
    ├─→ Entity Lookup Endpoint (GET /entities)
    └─→ Entity Search Endpoint (GET /entities/search)

Caching Layer (optional but recommended for performance)
    ↓
    └─→ Depends on: Entity Sentiment Endpoint, Trending Detection, Multi-Entity Batch Query
```

## MVP Recommendation

For MVP (v1), prioritize in this order:

1. **Article Ingestion + Deduplication** — Ingest news and Reddit from AskNews, deduplicate articles by content hash/URL
2. **Sentiment Time-Series Storage** — Store article-level sentiment, compute hourly/daily aggregates
3. **Entity Sentiment Endpoint** — GET `/entities/{id}/sentiment?start_date=&end_date=` — core frontend feature
4. **Scheduled Polling** — Reliable, consistent data collection (15-min news, 60-min stories)
5. **Entity Lookup** — GET `/entities` and GET `/entities/search?q=...` for frontend autocomplete
6. **Source Separation** — Track news vs Reddit sentiment separately; return in aggregation endpoint
7. **Historical Retention** — Ensure data persists across restarts; define retention policy (6-12 months)

**One Differentiator for v1:** Entity Comparison Endpoint (GET `/entities/compare?ids=...`) — low complexity, high value for frontend. Allows side-by-side sentiment comparison, differentiates from generic dashboards.

**Defer to v2 (if users ask):**
- Trending detection (complexity unclear, low initial demand)
- Caching layer (add only if query latency becomes issue)
- Sentiment velocity/momentum (requires 30+ days of historical data)
- Source-level attribution (nice to have, moderate complexity)
- Custom aggregation granularity (preset hourly/daily sufficient for v1)

## Feature Complexity Assessment

| Feature | Implementation Size | Duration | Risk |
|---------|-------------------|----------|------|
| Article Ingestion | 2-3 days | Low | AskNews SDK works well; main risk is handling rate limits |
| Deduplication | 1 day | Low | Content hashing straightforward; test with real data |
| Time-Series Aggregation | 2-3 days | Medium | SQL query design for rollups; need to test at scale |
| Entity Sentiment Endpoint | 1-2 days | Low | Query builder, response formatting |
| Scheduled Polling | 1-2 days | Low | APScheduler + state tracking; main risk is idempotency bugs |
| Entity Lookup | 1 day | Low | Simple table scan + search |
| Source Separation | 1-2 days | Low | Add source_type column, update aggregation queries |
| Caching | 2-3 days | High | Cache invalidation is hard; only add if needed |
| Entity Comparison | 1-2 days | Low | Parallel queries, response formatting |
| Trending Detection | 2-3 days | Medium | Statistical spike detection; hard to tune thresholds |
| Sentiment Velocity | 1-2 days | Medium | Linear regression or moving average; test accuracy |

## Data Freshness Guarantees (Implications)

| Guarantee Level | What It Means | Complexity | Implementation |
|-----------------|---------------|-----------|-----------------|
| **Best-effort (v1)** | Data is usually fresh within 1 hour; gaps possible if ingestion fails | Low | Schedule polling; don't retry aggressively |
| **Guaranteed within N hours** | Data is always within 24h (hourly) or 7d (daily) of newest; requires monitoring | Medium | Monitor ingestion success rate; alert on gaps; implement catch-up logic |
| **Real-time (v2+)** | Sentiment updates within minutes; requires message queue + event streaming | High | Kafka/RabbitMQ, WebSocket frontend, event sourcing |

**Recommendation for v1:** Best-effort with monitoring. Report data freshness in API responses so frontend knows "last article ingested at 2026-02-05T14:32:00Z".

## Sources

- Domain expertise: Sentiment tracking backends (Meltwater, Brandwatch, Sprinklr patterns)
- Time-series data design patterns (InfluxDB, Timescale best practices)
- REST API design for time-series (GitHub API, New Relic API patterns)
- News aggregation patterns (Feedly, Inoreader, news API design)
- Common mistakes: Observed in production systems, avoided via this research

---

**Quality Gate:**
- [x] Categories are clear (table stakes vs differentiators vs anti-features)
- [x] Complexity noted for each feature
- [x] Dependencies between features identified
