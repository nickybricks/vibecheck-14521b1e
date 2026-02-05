# Domain Pitfalls: Python Backend + API Polling + Time-Series Data Pipeline

**Project:** VibeCheck
**Domain:** Python data pipeline with scheduled API polling, PostgreSQL time-series storage, and REST API serving
**Researched:** 2026-02-05
**Confidence:** MEDIUM-HIGH (training data + domain pattern knowledge, not current ecosystem search)

---

## Executive Summary

Building a scheduled data pipeline that polls external APIs and stores time-series data in PostgreSQL introduces multiple failure modes that commonly catch teams off-guard:

1. **Rate limiting surprises** — Apparent budget headroom vanishing when edge cases trigger unexpected API calls
2. **Database schema regrets** — Naive time-series schemas that work at 100 records/day but collapse at 10K records/day
3. **Scheduler reliability gaps** — Tasks that silently fail to run or run multiple times when deployed to production
4. **Entity matching complexity** — Name variation handling becoming a data quality problem when inconsistencies compound
5. **Monorepo friction** — Python and JavaScript environments fighting for control in shared repository
6. **Cost control blindness** — No visibility into what's consuming API budget until the bill arrives

Most critical: **Silent failures in production.** Scheduled tasks fail silently, duplicate data accumulates unseen, and rate limits are hit without alerting. Single-developer teams especially vulnerable because one person can't monitor everything.

---

## Critical Pitfalls

Mistakes that cause rewrites, production outages, or major data quality issues.

### Pitfall 1: Unexpected API Cost Overruns from Edge Cases

**What goes wrong:**

You budget for baseline API calls (10 entities × 4 calls/hour = 40 calls/hour = ~28,800 calls/month), but production hits 2-3x that:
- Retry logic retrying failed requests exponentially (asking AskNews for the same entity 5-10 times in a row)
- Clock skew causing duplicate overlapping queries (15-min job scheduled, but previous run still executing when next one starts)
- Error handling missing, causing retry storms when API is temporarily down
- Entity filtering too broad accidentally (e.g., searching "GPT" matches "GPT-4o", "GPT-4-Turbo", "GPT-J", "GPT-2", etc.)
- Testing queries against production API without rate limit protection
- Background job pool exhausted, jobs queuing up and making duplicate requests

**Why it happens:**

- Easy to assume "I'll just retry if it fails" without considering exponential backoff
- Clock skew between local time and server time is invisible until production
- AskNews entity filtering documentation (GLiNER-based) has nuances you don't discover until live
- Single developer has no production monitoring setup, so issues are discovered by bill, not by alerting

**Consequences:**

- Monthly AskNews bill becomes $800-1,200 instead of $250 (the whole budget)
- Accounts get throttled or suspended for exceeding rate limits
- Data collection stops unexpectedly mid-cycle
- Wasted engineering time investigating why billing is high (post-incident)

**Prevention:**

1. **Hard cap on API calls:**
   - Track API calls in-process with a counter that stops scheduling new jobs when threshold is hit
   - Log total daily API call count at end-of-day
   - Set alerts for >100% of baseline (notify at 2,500-3,000 calls/day for your case)

   ```python
   # In scheduler initialization
   api_call_budget = 5000  # Based on tier, with 30% safety margin
   calls_made_today = 0  # Reset at midnight UTC

   async def poll_news_with_budget():
       global calls_made_today
       if calls_made_today > api_call_budget:
           logger.warning(f"API budget exhausted today: {calls_made_today}")
           return

       try:
           calls_made_today += 1
           # Make call...
       except Exception as e:
           # Backoff retry with exponential delay + max retries
           logger.error(f"API call failed: {e}, will retry")
   ```

2. **Explicit retry policy with backoff:**
   - Max 3 retries, exponential backoff (1s, 4s, 16s), jitter to avoid thundering herd
   - Never retry on 4xx errors (not coming back), only on 5xx or timeout

   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential

   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=16))
   async def call_asknews(entity):
       # Only retries on transient errors, not auth failures
       pass
   ```

3. **Deduplicate requests before making them:**
   - Query database for latest data timestamp per entity
   - Don't request data older than what you already have
   - Store `last_successful_poll` per entity, don't re-query if within 15 mins

   ```python
   async def should_poll_entity(entity_id):
       last_poll = await db.get_last_poll_time(entity_id)
       if last_poll and (datetime.now(UTC) - last_poll) < timedelta(minutes=15):
           logger.debug(f"Skipping {entity_id}, polled {seconds_ago}s ago")
           return False
       return True
   ```

4. **Test against API without modifying budget:**
   - Use AskNews sandbox tier or cached responses during development
   - Never run live polls against production API during testing
   - Store fixture responses locally for integration tests

5. **Explicit scheduling constraints:**
   - Use database locks to prevent concurrent runs of same job
   - Set APScheduler `misfire_grace_time=60` to drop jobs that couldn't run on time
   - Log when jobs are skipped due to concurrency protection

   ```python
   from apscheduler.schedulers.background import BackgroundScheduler

   scheduler = BackgroundScheduler(timezone='UTC')
   scheduler.add_job(
       poll_news,
       'interval',
       minutes=15,
       id='poll_news',
       name='Poll AskNews News Endpoint',
       misfire_grace_time=60,  # Don't run if >1min late
       max_instances=1,  # Never run multiple times simultaneously
       replace_existing=True,
   )
   ```

**Detection / Warning Signs:**

- [ ] Monthly billing spike without corresponding data growth
- [ ] API rate limit errors appearing in logs (429 responses)
- [ ] Same entity records appearing multiple times from same time window
- [ ] Database growing faster than expected (>100K records in first week)
- [ ] Slow query performance even though data size seems small

**Phase for Mitigation:** Phase 1 (Foundation)
This must be in place before any production deployment. Rate limiting is not an enhancement, it's a prerequisite.

---

### Pitfall 2: PostgreSQL Time-Series Schema Collapses Under Scale

**What goes wrong:**

Initial schema works fine:

```sql
CREATE TABLE articles (
    id SERIAL PRIMARY KEY,
    entity_name VARCHAR(100),
    title VARCHAR(500),
    url VARCHAR(2000) UNIQUE,
    sentiment FLOAT,
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_entity_created ON articles(entity_name, created_at);
```

But at scale (10K+ records), you hit:
- **Bloat:** No partitioning, so table becomes 500MB+, index scans slow
- **Lock contention:** Every insert locks the UNIQUE constraint check on `url`, causing timeouts during bulk inserts
- **No time-series aggregation efficiency:** Queries like "sentiment daily average per entity" scan entire table instead of pre-aggregated data
- **Uncontrolled data growth:** No retention policy, articles from month 1 still in table
- **Slow timezone handling:** All timestamps stored in DB's timezone, conversions required on every query
- **Bloated backups:** Entire articles table backed up even though you only need to keep 90 days

**Why it happens:**

- Initial data volume is small, so naive schema "works"
- Sentiment analytics thought to be slow queries (select avg(sentiment), so you pre-aggregate), but pre-aggregation logic has bugs
- No one planned for scale because "it's just a monitoring dashboard"
- UNIQUE constraints seem necessary but cause blocking during batch inserts

**Consequences:**

- Insert performance degradation (from 100ms to 5s per record)
- Analytics queries timeout (select for last 30 days by entity takes 30+ seconds)
- Backup/restore takes hours instead of minutes
- Data deletion is risky (removes 1 year of history accidentally instead of 90-day old records)
- Difficult to re-partition or migrate schema without downtime

**Prevention:**

1. **Use TimescaleDB extension (CRITICAL):**
   - Purpose-built for time-series, handles compression, auto-partitioning, and retention
   - Convert your `articles` table to a hypertable, gets 10-100x better query performance
   - Automatic data retention (drop data older than 90 days)

   ```sql
   -- Install extension
   CREATE EXTENSION IF NOT EXISTS timescaledb;

   -- Create hypertable (TimescaleDB partitions by time automatically)
   CREATE TABLE articles (
       id SERIAL,
       entity_id INTEGER NOT NULL,
       title VARCHAR(500),
       url VARCHAR(2000) NOT NULL,
       sentiment FLOAT,
       published_at TIMESTAMP NOT NULL,
       created_at TIMESTAMP NOT NULL DEFAULT NOW(),
       PRIMARY KEY (id, created_at)
   );

   SELECT create_hypertable('articles', 'created_at', if_not_exists => TRUE);

   -- Auto-delete data older than 90 days
   SELECT add_retention_policy('articles', INTERVAL '90 days', if_not_exists => TRUE);

   -- Create indexes (TimescaleDB optimizes automatically)
   CREATE INDEX idx_entity_published ON articles(entity_id, published_at DESC);
   ```

   **Confidence:** HIGH (TimescaleDB is standard for PostgreSQL time-series)

2. **Separate tables for aggregates:**
   - Don't store raw articles and query averages from them
   - Pre-compute `entity_sentiment_hourly` and `entity_sentiment_daily` tables
   - Refresh these nightly via batch job, queries hit aggregates instead of raw data

   ```sql
   CREATE TABLE entity_sentiment_hourly (
       entity_id INTEGER NOT NULL,
       hour TIMESTAMP NOT NULL,
       avg_sentiment FLOAT,
       count INTEGER,
       PRIMARY KEY (entity_id, hour)
   );

   SELECT create_hypertable('entity_sentiment_hourly', 'hour',
       if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day');
   ```

3. **Remove or defer UNIQUE constraints on URLs:**
   - Use `url` column but don't enforce uniqueness at DB level (check in application logic)
   - Uniqueness constraint locks every insert, slowing down batch operations
   - Store `url_hash` (SHA256) instead for faster comparison
   - Check for duplicates before inserting, but don't rely on database constraint

   ```python
   import hashlib

   async def insert_article(article):
       url_hash = hashlib.sha256(article['url'].encode()).hexdigest()
       existing = await db.query(
           "SELECT id FROM articles WHERE url_hash = %s LIMIT 1",
           (url_hash,)
       )
       if existing:
           return  # Skip duplicate

       await db.execute(
           "INSERT INTO articles (title, url, url_hash, sentiment) VALUES ...",
           (article['title'], article['url'], url_hash, article['sentiment'])
       )
   ```

4. **Batch inserts instead of single-row:**
   - Not `INSERT INTO articles VALUES (...)` 100 times
   - Collect 100 records, then `INSERT INTO articles VALUES (...), (...), ... (...)`
   - 100x faster for bulk loads

   ```python
   from psycopg.rows import dict_row

   async def bulk_insert_articles(articles: list[dict]):
       if not articles:
           return

       query = """
           INSERT INTO articles (title, url, sentiment, published_at)
           VALUES %s
           ON CONFLICT DO NOTHING  -- Handle duplicates gracefully
       """

       values = [(a['title'], a['url'], a['sentiment'], a['published_at'])
                 for a in articles]

       await db.execute(query, values)
   ```

5. **Explicit retention policy from day 1:**
   - Define what data you keep and for how long (90 days? 1 year?)
   - Build cleanup into your schema and run it weekly
   - Never delete data without understanding impact on analytics

   ```python
   # In maintenance job, run weekly
   async def cleanup_old_articles():
       deleted = await db.execute(
           "DELETE FROM articles WHERE created_at < NOW() - INTERVAL '90 days'"
       )
       logger.info(f"Cleaned up {deleted} old articles")
   ```

6. **Store UTC timestamps, not local time:**
   - All timestamps in UTC (`created_at TIMESTAMP WITH TIME ZONE`)
   - Convert to user's timezone in application, not in database
   - Prevents time-zone related bugs and makes aggregations consistent

   ```sql
   CREATE TABLE articles (
       created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),  -- UTC
       published_at TIMESTAMP WITH TIME ZONE NOT NULL  -- UTC
   );
   ```

**Detection / Warning Signs:**

- [ ] Insert performance slows as table grows (>10 seconds per insert)
- [ ] "SELECT avg(sentiment) ... WHERE created_at > now() - interval '7 days'" takes >5 seconds
- [ ] Index bloat reported by `pgstattuple` extension
- [ ] Backup size unexpectedly large (>1GB for 1 month of data)
- [ ] Table has >500MB size but only 30 days of data

**Phase for Mitigation:** Phase 1 (Foundation)
Schema design must be correct before any data enters production. Changing schema later is expensive and risky.

---

### Pitfall 3: Scheduler Reliability — Silent Task Failures in Production

**What goes wrong:**

You deploy your scheduler (APScheduler, Celery, or home-grown cron), and it works locally. Then in production:
- **Job fails but nobody notices:** Exception is caught, logged, and silently swallowed. No alert. Data collection stops.
- **Job runs but database connection is dead:** APScheduler task executes, tries to insert data, gets `connection refused`, rolls back. No retry.
- **Task runs twice simultaneously:** Clock skew causes two poll jobs to start at same time. Both make API calls. Both write data. Now you have duplicates.
- **Scheduler doesn't start on app boot:** FastAPI starts, loads routes, but scheduler initialization fails silently (exception in `@app.on_event("startup")` is not visible).
- **Task result is lost:** If using Celery with in-memory broker, results disappear if process restarts.
- **Cron job vs async task confusion:** You schedule a cron job in SystemD, but also have APScheduler running. Both fire simultaneously.

**Why it happens:**

- Schedulers are "fire and forget" — designed to minimize overhead, not to guarantee reliability
- Application-level schedulers (APScheduler) don't persist state, so restarting the app can lose upcoming job runs
- No observability: scheduled tasks don't appear in logs by default, and failure to run is not logged
- Single developer has one running instance, so scheduler crashes = data collection stops until restart

**Consequences:**

- Data gaps (3 days of missing sentiment data because scheduler crashed)
- Duplicate data accumulating (same articles inserted twice)
- Inconsistent state (one entity has data through Tuesday, another through Monday)
- Silent failures mean you discover the problem weeks later when customer reports missing data
- Debugging is painful (no way to know when job last ran or why it failed)

**Prevention:**

1. **Use Celery with persistent broker (not APScheduler for critical jobs):**
   - APScheduler is okay for non-critical background work
   - For polling that drives your product, use Celery + Redis or Celery + PostgreSQL
   - Celery persists job state, handles retries, and has monitoring tools

   ```python
   from celery import Celery, shared_task
   from celery.schedules import schedule

   app = Celery('vibecheck')
   app.conf.update(
       broker_url='redis://localhost:6379/0',
       result_backend='redis://localhost:6379/0',
       timezone='UTC',
       task_serializer='json',
       accept_content=['json'],
       result_serializer='json',
   )

   # Define periodic tasks
   app.conf.beat_schedule = {
       'poll-news': {
           'task': 'tasks.poll_news',
           'schedule': schedule(run_every=15 * 60),  # 15 minutes
       },
       'poll-stories': {
           'task': 'tasks.poll_stories',
           'schedule': schedule(run_every=60 * 60),  # 1 hour
       },
   }

   @shared_task(bind=True, max_retries=3, default_retry_delay=60)
   def poll_news(self):
       try:
           # Do polling work
           pass
       except Exception as exc:
           # Auto-retry with exponential backoff, up to 3 times
           raise self.retry(exc=exc, countdown=60)
   ```

   **Rationale:** Celery is battle-tested for scheduling, has built-in retry logic, and integrates with monitoring tools like Flower.

2. **If using APScheduler, add health check:**
   - Log every job start and completion
   - Expose `/health` endpoint that checks when each job last ran
   - Alert if any job hasn't run in expected window (e.g., > 30 mins for 15-min job)

   ```python
   from datetime import datetime, timedelta, UTC

   job_last_run = {}  # {job_name: datetime}

   def schedule_poll_job():
       def job_wrapper():
           try:
               job_last_run['poll_news'] = datetime.now(UTC)
               logger.info("Starting poll_news job")
               poll_news()
               logger.info("Completed poll_news job")
           except Exception as e:
               logger.exception(f"poll_news job failed: {e}")
               # CRITICAL: Send alert here, don't just log
               send_alert(f"Scheduled job poll_news failed: {e}")

       scheduler.add_job(job_wrapper, 'interval', minutes=15, id='poll_news')

   @app.get('/health')
   async def health():
       for job_name, last_run in job_last_run.items():
           age = datetime.now(UTC) - last_run
           expected_interval = 15 if job_name == 'poll_news' else 60

           if age > timedelta(minutes=expected_interval * 2):
               return {
                   'status': 'unhealthy',
                   'reason': f'{job_name} last ran {age.total_seconds()}s ago'
               }, 503

       return {'status': 'healthy'}
   ```

3. **Explicit concurrency control with database lock:**
   - Prevent same job from running twice via database-level lock
   - Use `SELECT ... FOR UPDATE SKIP LOCKED` to implement distributed locks
   - If job is already running, skip this invocation instead of waiting

   ```python
   async def poll_news_with_lock():
       async with db.transaction():
           # Try to acquire lock, skip if can't get it immediately
           locked = await db.execute("""
               SELECT 1 FROM job_locks
               WHERE job_id = 'poll_news'
               FOR UPDATE SKIP LOCKED
               LIMIT 1
           """)

           if not locked:
               logger.debug("poll_news already running, skipping this invocation")
               return

           # Do the work
           await poll_news()
   ```

4. **Explicit startup verification:**
   - On app startup, verify that scheduler is running
   - Check that no jobs are stuck (haven't run in way too long)
   - Log the scheduler status clearly

   ```python
   @app.on_event("startup")
   async def startup():
       try:
           scheduler.start()
           logger.info("Scheduler started successfully")

           # Verify all expected jobs are registered
           jobs = scheduler.get_jobs()
           expected = {'poll_news', 'poll_stories'}
           actual = {job.id for job in jobs}

           if expected != actual:
               logger.error(f"Scheduler jobs mismatch! Expected {expected}, got {actual}")
               raise RuntimeError("Scheduler configuration incomplete")

       except Exception as e:
           logger.critical(f"Failed to start scheduler: {e}")
           raise  # Don't start app if scheduler can't start
   ```

5. **Run scheduler in separate process:**
   - Don't run scheduler in same process as API server
   - If API crashes, scheduler also crashes and data collection stops
   - Run Celery Beat in separate systemd/docker service, communicates with API via message queue

   ```bash
   # Separate systemd services

   # Service 1: FastAPI web server
   [Unit]
   Description=VibeCheck API
   After=network.target

   [Service]
   ExecStart=/usr/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000

   # Service 2: Celery Beat scheduler
   [Unit]
   Description=VibeCheck Celery Beat
   After=redis.service

   [Service]
   ExecStart=/usr/bin/python -m celery -A tasks beat --loglevel=info
   ```

6. **Log job execution explicitly:**
   - Every job start and end should be logged with timestamp
   - Every failure should be logged with full traceback
   - Store execution log in database for audit trail

   ```python
   @shared_task
   def poll_news():
       execution_id = str(uuid.uuid4())
       logger.info(f"[{execution_id}] poll_news START")

       try:
           articles = fetch_from_asknews()
           await db.execute(
               "INSERT INTO scheduled_execution_log (execution_id, job_name, status) VALUES (%s, %s, %s)",
               (execution_id, 'poll_news', 'success')
           )
           logger.info(f"[{execution_id}] poll_news SUCCESS ({len(articles)} articles)")
       except Exception as e:
           logger.exception(f"[{execution_id}] poll_news FAILED: {e}")
           await db.execute(
               "INSERT INTO scheduled_execution_log (execution_id, job_name, status, error) VALUES (%s, %s, %s, %s)",
               (execution_id, 'poll_news', 'failure', str(e))
           )
           raise
   ```

**Detection / Warning Signs:**

- [ ] Data gaps in time-series (no articles for entity X on day 3)
- [ ] Duplicate articles appearing (same URL inserted twice with slight timestamp difference)
- [ ] No logs from scheduled jobs (scheduler is running but not logging)
- [ ] Scheduler health check endpoint fails but app is still running
- [ ] Data collection stopped after server restart (scheduler didn't re-initialize)

**Phase for Mitigation:** Phase 1 (Foundation)
Scheduler reliability must be confirmed before any production deployment. Data collection is the core value, so scheduler is non-negotiable.

---

### Pitfall 4: Entity Matching and Name Variation Explosion

**What goes wrong:**

You start with a fixed entity list:
- GPT-4o
- Claude
- Gemini
- Cursor
- v0

But in real news, these names appear as:
- "GPT-4o", "GPT 4o", "gpt-4o", "OpenAI's GPT-4o", "GPT-4-O", "GPT4o"
- "Anthropic Claude", "Claude 3", "Claude Opus", "claude-3-opus"
- "Google Gemini", "Gemini 1.5", "gemini-pro"
- "Anysphere Cursor", "Cursor IDE", "cursor-ai"
- "v0", "Vercel v0", "v0.dev"

And your entity filter in AskNews (`string_guarantee`) matches some but not all. So you get:
- **Inconsistent entity attribution:** Same article about Claude shows up under multiple names
- **Entity name fragmentation:** "Claude" and "Claude 3" are tracked separately, making analysis wrong
- **Missed articles:** Articles about "Claude Opus" don't match entity filter, so sentiment data for that period is incomplete
- **Duplicate entity records:** Database has 50 variations of "GPT-4o" instead of 1, so grouping by entity_name fails
- **Impossible to fix retroactively:** 6 months of data is split across variations, combining them requires full re-processing

**Why it happens:**

- AskNews GLiNER entity extraction works on ML model (not 100% accurate), and entity filter is simple substring matching
- News writers use abbreviations and variations naturally ("GPT4" vs "GPT-4", "Cursor" vs "Cursor IDE")
- Name variations not discovered until you have real data (you don't know "Cursor IDE" appears more than "Cursor")
- Single developer can't manually curate entity matching rules as they appear

**Consequences:**

- Analytics show entity sentiment incorrectly (Claude's sentiment split across variants)
- Customer reports "we're missing Claude articles" because they appear as "Claude 3"
- Manual data cleanup required (UPDATE statements to consolidate variants)
- Loss of historical data integrity (can't trust early sentiment averages)

**Prevention:**

1. **Entity normalization at insertion time (not in UI):**
   - Define canonical names and variations upfront
   - Normalize entity names when inserting articles
   - Map all variations to canonical name in database

   ```python
   # entities.py
   ENTITY_VARIATIONS = {
       'gpt_4o': {
           'canonical': 'GPT-4o',
           'variations': [
               'GPT-4o', 'GPT 4o', 'gpt-4o', 'GPT4o', 'GPT-4-O',
               "OpenAI's GPT-4o", 'GPT-4o mini', 'GPT 4o mini'
           ]
       },
       'claude': {
           'canonical': 'Claude',
           'variations': [
               'Claude', 'claude', 'Anthropic Claude', 'Claude 3',
               'Claude Opus', 'Claude Sonnet', 'Claude Haiku'
           ]
       },
       'cursor': {
           'canonical': 'Cursor',
           'variations': [
               'Cursor', 'cursor', 'Cursor IDE', 'Anysphere Cursor',
               'cursor-ai'
           ]
       },
   }

   async def normalize_entity_name(extracted_name: str) -> str | None:
       """Map extracted entity name to canonical form, or None if not recognized."""
       if not extracted_name:
           return None

       normalized = extracted_name.strip().lower()

       for entity_key, entity_data in ENTITY_VARIATIONS.items():
           for variation in entity_data['variations']:
               if variation.lower() in normalized or normalized in variation.lower():
                   return entity_data['canonical']

       return None  # Entity not in curated list

   async def insert_article_with_normalization(article):
       """Insert article, normalizing entity name."""
       canonical_entity = normalize_entity_name(article.get('entity_name'))

       if not canonical_entity:
           logger.debug(f"Article entity '{article.get('entity_name')}' not in curated list, skipping")
           return  # Skip articles about non-curated entities

       await db.execute("""
           INSERT INTO articles (entity_name, title, url, sentiment)
           VALUES (%s, %s, %s, %s)
       """, (canonical_entity, article['title'], article['url'], article['sentiment']))
   ```

2. **Explicit entity matching in AskNews query filters:**
   - Don't rely on GLiNER's entity extraction + substring matching
   - Use AskNews `string_guarantee` to enforce strict matching
   - Query with explicit search terms for each entity

   ```python
   # Instead of generic entity search, search for specific entity variants
   async def poll_entity(entity_name):
       """Query AskNews with explicit terms for this entity."""
       search_terms = ENTITY_VARIATIONS[entity_name]['variations']

       results = []
       for term in search_terms:
           response = await asknews_client.news.search(
               query=term,
               string_guarantee=[term],  # Strict: term must appear in results
               limit=10,
               sort_by='date'
           )
           results.extend(response.articles)

       # Deduplicate by URL
       unique_results = {article.url: article for article in results}
       return list(unique_results.values())
   ```

3. **Entity matching audit trail:**
   - Store original extracted name alongside normalized name in database
   - Track which variation matched which article
   - Use this to validate normalization rules and find edge cases

   ```sql
   ALTER TABLE articles ADD COLUMN extracted_entity_name VARCHAR(200);

   -- Insert with both names
   INSERT INTO articles (entity_name, extracted_entity_name, title, url, sentiment)
   VALUES ('GPT-4o', 'GPT 4o', ..., ..., ...);

   -- Query to find unmapped entities
   SELECT extracted_entity_name, COUNT(*) as count
   FROM articles
   WHERE entity_name IS NULL
   GROUP BY extracted_entity_name
   ORDER BY count DESC;
   ```

4. **Validation of entity mapping before production:**
   - Test entity normalization against real articles
   - Manually verify that top 100 articles are normalized correctly
   - Don't assume rules will work until they're tested against real data

   ```python
   async def validate_entity_normalization():
       """Test normalization against recent articles."""
       # Fetch recent articles from AskNews without filters
       all_articles = await asknews_client.news.search(limit=100)

       mapped = 0
       unmapped = 0

       for article in all_articles:
           canonical = normalize_entity_name(article.entity_name)
           if canonical:
               mapped += 1
           else:
               unmapped += 1
               if unmapped <= 10:  # Log first 10 unmapped
                   logger.info(f"Unmapped entity: '{article.entity_name}' in {article.title}")

       coverage = mapped / len(all_articles) * 100
       logger.info(f"Entity coverage: {coverage:.1f}% ({mapped}/{len(all_articles)})")

       if coverage < 50:  # Alert if <50% of articles match curated list
           logger.warning(f"Low entity coverage! Only matching {coverage:.1f}% of articles")
   ```

5. **Periodic audit of entity variations:**
   - Quarterly review of extracted entity names in database
   - Find new variations that appeared in real data
   - Update ENTITY_VARIATIONS rules based on patterns
   - This catches edge cases you didn't anticipate

   ```python
   async def audit_unmapped_entities(days=30):
       """Find entity names that weren't normalized in recent period."""
       query = """
           SELECT extracted_entity_name, COUNT(*) as count
           FROM articles
           WHERE entity_name IS NULL
           AND created_at > NOW() - INTERVAL '%s days'
           GROUP BY extracted_entity_name
           ORDER BY count DESC
           LIMIT 20
       """

       unmapped = await db.fetch(query, (days,))

       if unmapped:
           logger.warning(f"Top unmapped entities (last {days} days):")
           for row in unmapped:
               logger.warning(f"  {row['extracted_entity_name']}: {row['count']} articles")

           # Send notification to developer to review
           send_slack_message(f"Entity audit: {len(unmapped)} unmapped variations found")
   ```

**Detection / Warning Signs:**

- [ ] Same article appearing under multiple entity names
- [ ] Entity sentiment averages wildly inconsistent (Claude sentiment changes 50 points when new variant appears)
- [ ] User reports "missing articles about X entity"
- [ ] `SELECT COUNT(*) FROM articles GROUP BY entity_name` shows many similar names (claude, Claude, CLAUDE, Anthropic Claude)
- [ ] Normalization rules broke when new article about "Claude Code Interpreter" appeared

**Phase for Mitigation:** Phase 1 (Foundation)
Entity mapping must be correct from the start. It's easier to design once than to fix retroactively. Use a separate entity curation phase if needed, but don't deploy polling without entity mapping validation.

---

### Pitfall 5: Monorepo Python + JavaScript Dependency Conflicts

**What goes wrong:**

You have frontend in `/` and backend in `/backend`, sharing some files or utilities:

```
vibecheck/
├── package.json        (frontend)
├── backend/
│   ├── requirements.txt (backend)
│   ├── pyproject.toml
│   └── src/
└── shared/             (shared code? utilities?)
```

Problems that emerge:
- **Environment bleeding:** Node.js tools (npm) interfere with Python tools (pip). Running `npm install` somehow affects `python -m venv`.
- **Shared types:** Frontend and backend define the same data types. Update one, break the other.
- **Conflicting runtime versions:** Frontend needs Node.js 20.x, backend needs Python 3.11, but deployment only installs Node.
- **Build order confusion:** Does `npm build` need to run before `python -m build`? Vice versa?
- **Path confusion:** Python's `__file__` and JavaScript's `__dirname` behave differently. Relative paths break when deployed.
- **Testing confusion:** `npm test` runs frontend tests, but backend tests are `pytest`. New developer doesn't know how to run all tests.
- **Linting/formatting:** Black (Python) and Prettier (JS) fight over code style. Pre-commit hooks run different tools for different languages.

**Why it happens:**

- Monorepos are convenient for deployment, but Node.js and Python toolchains are fundamentally different
- No clear separation of concerns (which files are frontend-only, which are backend-only)
- Shared directory structure (e.g., `shared/` or `src/`) suggests code sharing, but Python and JavaScript can't share code meaningfully
- Single developer doesn't invest time in monorepo tooling (Nx, Turborepo), so it's ad-hoc

**Consequences:**

- New developer can't get project running (conflicting instructions for setup)
- CI/CD pipeline fails because build steps are in wrong order
- Accidental changes to backend when deploying frontend (or vice versa)
- Debugging is harder (is the issue in frontend or backend?)
- Hard to scale (e.g., deploying backend separately from frontend becomes complex)

**Prevention:**

1. **Explicit directory structure with clear boundaries:**

   ```
   vibecheck/
   ├── frontend/              # Vite + React + TypeScript (isolated)
   │   ├── package.json
   │   ├── src/
   │   ├── dist/
   │   └── README.md
   │
   ├── backend/               # FastAPI + Python (isolated)
   │   ├── pyproject.toml
   │   ├── requirements.txt
   │   ├── src/
   │   ├── tests/
   │   └── README.md
   │
   ├── .github/workflows/     # Shared CI/CD
   │   ├── test.yml           # Tests for both
   │   ├── deploy.yml
   │
   ├── docker-compose.yml     # Local development
   ├── .gitignore
   └── README.md              # Monorepo root instructions
   ```

   **Rationale:** Each runtime lives in its own directory with its own dependencies. No shared `src/` or `lib/` to cause confusion.

2. **Separate package managers and lock files:**
   - Frontend uses `package.json` + `package-lock.json`
   - Backend uses `pyproject.toml` + `requirements.lock` (via pip-tools or Poetry)
   - Never mix them

   ```bash
   # Frontend setup
   cd frontend
   npm install
   npm run dev

   # Backend setup (separate terminal)
   cd backend
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python -m uvicorn main:app --reload
   ```

3. **Docker Compose for local development (no manual setup):**
   - Eliminates "works on my machine" problems
   - Ensures frontend and backend can talk to each other
   - PostgreSQL and Redis run in containers too

   ```yaml
   version: '3.8'
   services:
     frontend:
       build: ./frontend
       ports:
         - "8080:8080"
       command: npm run dev
       volumes:
         - ./frontend:/app
       environment:
         - VITE_API_URL=http://localhost:8000

     backend:
       build: ./backend
       ports:
         - "8000:8000"
       command: uvicorn main:app --host 0.0.0.0 --reload
       volumes:
         - ./backend:/app
       depends_on:
         - postgres
       environment:
         - DATABASE_URL=postgresql://user:password@postgres:5432/vibecheck

     postgres:
       image: postgres:16-alpine
       environment:
         - POSTGRES_DB=vibecheck
         - POSTGRES_USER=user
         - POSTGRES_PASSWORD=password
       ports:
         - "5432:5432"
       volumes:
         - postgres_data:/var/lib/postgresql/data

     redis:
       image: redis:7-alpine
       ports:
         - "6379:6379"

   volumes:
     postgres_data:
   ```

4. **Unified test and lint commands:**
   - Create root-level scripts that run both frontend and backend tests
   - Make it clear how to test everything

   ```bash
   # Makefile or just a shell script

   test-frontend:
       cd frontend && npm test

   test-backend:
       cd backend && pytest

   test: test-frontend test-backend
       @echo "All tests passed"

   lint-frontend:
       cd frontend && npm run lint

   lint-backend:
       cd backend && black . --check && ruff check .

   lint: lint-frontend lint-backend

   format:
       cd frontend && npm run format
       cd backend && black . && ruff check --fix .
   ```

   Then developers run `make test` for everything, not trying to remember different commands.

5. **CI/CD pipeline that tests and deploys separately:**

   ```yaml
   name: Test & Deploy

   on: [push, pull_request]

   jobs:
     test-frontend:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-node@v3
           with:
             node-version: '20'
         - run: cd frontend && npm install && npm test

     test-backend:
       runs-on: ubuntu-latest
       services:
         postgres:
           image: postgres:16-alpine
           env:
             POSTGRES_PASSWORD: test
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.11'
         - run: |
             cd backend
             python -m pip install -r requirements.txt
             pytest

     deploy:
       if: github.ref == 'refs/heads/main' && success()
       needs: [test-frontend, test-backend]
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - run: |
             docker build -t vibecheck-frontend ./frontend
             docker build -t vibecheck-backend ./backend
             # Push to registry, deploy...
   ```

6. **Clear README for each component:**
   - Root `/README.md` explains monorepo structure
   - `frontend/README.md` explains frontend setup, build, test
   - `backend/README.md` explains backend setup, test, deployment
   - No ambiguity about how to set up the project

   ```markdown
   # VibeCheck Monorepo

   This is a monorepo with separate frontend (Vite/React) and backend (FastAPI) applications.

   ## Development Setup

   ```bash
   # Option 1: Docker (recommended for first-time setup)
   docker-compose up

   # Option 2: Manual setup
   # Frontend
   cd frontend && npm install && npm run dev

   # Backend (in another terminal)
   cd backend && python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   python -m uvicorn main:app --reload
   ```

   See `frontend/README.md` and `backend/README.md` for detailed instructions.
   ```

**Detection / Warning Signs:**

- [ ] Developer confusion about setup (multiple ways to run, doesn't match each other)
- [ ] Different GitHub Actions workflows for frontend and backend (not unified)
- [ ] Shared code with imports like `from ../backend import ...` in frontend
- [ ] Path issues in deployed app (relative paths assume wrong working directory)
- [ ] Deployment script updates either frontend OR backend, but not clear if both need deploying

**Phase for Mitigation:** Phase 0 (Planning) or Phase 1 (Foundation)
Get the monorepo structure right before any code is written. It's cheap to set up correctly, expensive to refactor later.

---

## Moderate Pitfalls

Mistakes that cause delays, technical debt, or operational pain (but not complete rewrites).

### Pitfall 6: Lack of Instrumentation and Observability

**What goes wrong:**

- No logging of API calls (when they succeeded/failed, how long they took, what data was returned)
- No monitoring of database performance (slow queries go unnoticed)
- No alerting on data quality issues (duplicates, gaps in time-series)
- Errors happen, but they're only discovered when customer complains

**Prevention:**

1. **Structured logging from day 1:**
   ```python
   import logging
   import json
   from datetime import datetime

   logger = logging.getLogger(__name__)

   async def poll_entity(entity_name):
       start = datetime.now(UTC)
       try:
           result = await asknews_client.news.search(...)
           duration = (datetime.now(UTC) - start).total_seconds()

           logger.info("API call succeeded", extra={
               'entity': entity_name,
               'articles_found': len(result.articles),
               'duration_seconds': duration,
               'api_request_id': result.request_id
           })

           return result
       except Exception as e:
           duration = (datetime.now(UTC) - start).total_seconds()
           logger.error("API call failed", exc_info=True, extra={
               'entity': entity_name,
               'duration_seconds': duration,
               'error_type': type(e).__name__
           })
           raise
   ```

2. **Monitor data quality metrics:**
   - Count of articles per entity per day (should be consistent)
   - Duplicate detection (URLs appearing twice)
   - Data gaps (entity with no data for >30 mins)

3. **Set up basic alerts:**
   - If data collection stops (no articles in last hour)
   - If API rate limit is hit
   - If database connection is lost

**Phase for Mitigation:** Phase 1 (Foundation)
Add logging and alerting before production. Catching issues early saves debugging time.

---

### Pitfall 7: Testing Database Integration in Development

**What goes wrong:**

- Tests create real PostgreSQL connections, slow down test suite
- Tests don't clean up properly, leave garbage data
- Tests pass locally with real database, fail in CI where database doesn't exist
- No way to test error handling (database connection lost, table locked, etc.)

**Prevention:**

1. **Use fixtures for database setup/teardown:**
   ```python
   @pytest.fixture
   async def db():
       async with create_db_connection() as conn:
           await conn.execute("BEGIN")
           yield conn
           await conn.execute("ROLLBACK")  # Cleanup
   ```

2. **Mock external API calls:**
   ```python
   @pytest.fixture
   def mock_asknews():
       with patch('asknews.Client') as mock:
           mock.news.search.return_value = {
               'articles': [
                   {'title': 'Test', 'entity': 'GPT-4o', 'sentiment': 0.5}
               ]
           }
           yield mock
   ```

**Phase for Mitigation:** Phase 2 (Core Backend)
Testing strategy needs to be in place before implementing polling logic.

---

### Pitfall 8: Sentiment Data Aggregation Logic Bugs

**What goes wrong:**

- Aggregation includes articles from wrong time period (timezone issues, off-by-one errors)
- Weighting wrong (treating all articles equally, but some are from small sources)
- Not handling NULL/missing sentiment values (skipping them vs treating as 0)
- Aggregation query takes 30 seconds because it's not indexed properly

**Prevention:**

1. **Explicit aggregation with clear parameters:**
   ```python
   async def get_entity_sentiment_daily(entity_id: int, date: datetime):
       """Get daily average sentiment for entity."""
       start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
       end_of_day = start_of_day + timedelta(days=1)

       result = await db.fetch("""
           SELECT
               entity_id,
               DATE(published_at) as date,
               COUNT(*) as article_count,
               AVG(sentiment) as avg_sentiment,
               MIN(sentiment) as min_sentiment,
               MAX(sentiment) as max_sentiment
           FROM articles
           WHERE entity_id = %s
               AND published_at >= %s
               AND published_at < %s
               AND sentiment IS NOT NULL
           GROUP BY entity_id, DATE(published_at)
       """, (entity_id, start_of_day, end_of_day))

       return result[0] if result else None
   ```

2. **Test aggregations against known data:**
   ```python
   async def test_daily_sentiment_aggregation():
       # Insert test data
       await db.execute("""
           INSERT INTO articles (entity_id, sentiment, published_at)
           VALUES
               (1, 0.5, '2025-02-05 10:00:00'),
               (1, 0.7, '2025-02-05 14:00:00'),
               (1, 0.3, '2025-02-06 08:00:00')
       """)

       # Test aggregation
       result = await get_entity_sentiment_daily(1, datetime(2025, 2, 5))
       assert result['avg_sentiment'] == 0.6  # (0.5 + 0.7) / 2
       assert result['article_count'] == 2
   ```

**Phase for Mitigation:** Phase 2 (Core Backend)
Sentiment aggregation should have test cases before deploying.

---

## Minor Pitfalls

Mistakes that cause annoyance or extra work but are fixable.

### Pitfall 9: Forgetting to Handle Timezones Consistently

**What goes wrong:**

- Some timestamps stored in UTC, some in local time
- Aggregations group by "day" but midnight varies by timezone
- User sees "sentiment for today" but it's actually "sentiment for UTC today"

**Prevention:**

- All timestamps stored in UTC (`TIMESTAMP WITH TIME ZONE`)
- All calculations done in UTC
- Convert to user's timezone only in API response

**Phase for Mitigation:** Phase 1 (Foundation)

---

### Pitfall 10: API Rate Limit Headers Ignored

**What goes wrong:**

- AskNews returns `X-RateLimit-Remaining` header
- You ignore it, make another request, hit limit
- Next request fails with 429 Too Many Requests

**Prevention:**

```python
async def call_asknews_respecting_limits(entity):
    response = await asknews_client.news.search(...)

    remaining = int(response.headers.get('X-RateLimit-Remaining', -1))
    reset_time = int(response.headers.get('X-RateLimit-Reset', -1))

    if remaining == 0:
        logger.warning(f"Rate limit nearly exhausted, waiting until {reset_time}")
        sleep_duration = reset_time - time.time()
        if sleep_duration > 0:
            await asyncio.sleep(sleep_duration + 1)  # Wait a bit extra to be safe

    return response
```

**Phase for Mitigation:** Phase 1 (Foundation)

---

## Phase-Specific Warnings

| Phase | Topic | Pitfall | Mitigation |
|-------|-------|---------|-----------|
| **Phase 1: Foundation** | Database schema | Naive time-series schema collapses at scale | Use TimescaleDB from day 1 |
| **Phase 1: Foundation** | Scheduler | Silent task failures go unnoticed | Implement health checks and alerts |
| **Phase 1: Foundation** | API costs | Unexpected API overages destroy budget | Hard cap API calls, implement backoff |
| **Phase 1: Foundation** | Entity matching | Name variations fragment data | Normalize entities at insertion time |
| **Phase 1: Foundation** | Monorepo structure | Python + JS toolchain conflicts | Explicit directory boundaries, Docker Compose |
| **Phase 2: Core Backend** | Data deduplication | Duplicate articles accumulate | Insert with `ON CONFLICT DO NOTHING` |
| **Phase 2: Core Backend** | Sentiment aggregation | Buggy aggregation logic | Test against known data |
| **Phase 2: Core Backend** | Testing | Tests tightly coupled to real database | Use fixtures and mocks |
| **Phase 3: API & Frontend Integration** | Data freshness | Stale cache causes outdated sentiment | Implement cache invalidation |
| **Phase 3: API & Frontend Integration** | Pagination | Large datasets cause slow queries | Limit results, add offset/limit parameters |

---

## Summary Table: Quick Reference

| Pitfall | Severity | Detection | Phase Fix |
|---------|----------|-----------|-----------|
| **API cost overruns** | Critical | Monthly bill is 2-3x budget | Phase 1 |
| **Scheduler failures** | Critical | Data gaps, no logs | Phase 1 |
| **Time-series schema issues** | Critical | Query slowdown at 10K records | Phase 1 |
| **Entity name fragmentation** | Critical | Same entity appears as 10 variations | Phase 1 |
| **Monorepo conflicts** | High | Conflicting setup instructions | Phase 1 |
| **No observability** | High | Issues discovered by customer reports | Phase 1 |
| **Database testing issues** | Medium | Tests pass locally, fail in CI | Phase 2 |
| **Timezone bugs** | Medium | Off-by-one errors in daily aggregations | Phase 1 |
| **Rate limit ignoring** | Medium | 429 errors during production | Phase 1 |
| **Aggregation logic bugs** | Medium | Wrong sentiment averages | Phase 2 |

---

## Sources & References

**Confidence Levels:**
- HIGH: Core Python/PostgreSQL/FastAPI patterns from training data (Feb 2025 cutoff)
- MEDIUM: Common pitfalls in scheduled data pipelines from industry patterns

**Key Technologies Referenced:**
- **APScheduler:** Python in-process scheduler (training knowledge)
- **Celery:** Distributed task queue (training knowledge)
- **TimescaleDB:** PostgreSQL time-series extension (training knowledge, standard approach)
- **FastAPI:** Python async web framework (training knowledge)
- **AskNews API:** Based on project context (provided)

**Not Verified:**
- Current AskNews API rate limiting behavior (no access to official docs)
- Specific PostgreSQL version limitations (assumed modern 14+)
- Exact pricing tiers (based on project context)

---

**Last Updated:** 2026-02-05
**Phase Targeting:** Phase 1 focus (foundation must be rock-solid)
**Roadmap Implications:** Pitfalls inform feature phasing — database schema and scheduler reliability are prerequisites, not follow-ups.
