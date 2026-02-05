"""News polling job with retry logic and deduplication.

Fetches articles from AskNews News Search endpoint every 15 minutes (scheduling in Plan 04).
Handles API failures gracefully with exponential backoff and continues processing
remaining entities even if one fails.
"""
import structlog
from datetime import datetime
from typing import Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.clients.asknews_client import AskNewsClient
from pipeline.services.storage_service import batch_insert_articles
from utils.constants import ENTITY_NAMES

logger = structlog.get_logger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=16),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True
)
async def fetch_from_asknews_with_retry(
    entity_name: str,
    client: AskNewsClient
) -> list[dict[str, Any]]:
    """Fetch news articles with exponential backoff retry logic.

    Retries up to 3 times on transient network errors (TimeoutError, ConnectionError).
    Wait time: 1s, 2s, 4s (capped at 16s).

    Args:
        entity_name: Canonical entity name to fetch news for
        client: AskNews SDK client instance

    Returns:
        List of article dicts from AskNews API

    Raises:
        Exception: After 3 failed retry attempts

    Note:
        API plan limit: 10 articles per request (free tier)
    """
    logger.debug("fetching_with_retry", entity=entity_name)
    return await client.fetch_news(entity_name=entity_name, limit=10)


async def poll_news_job(db_session: AsyncSession) -> dict[str, Any]:
    """Poll news articles for all curated entities with per-entity error handling.

    For each entity in ENTITY_NAMES:
    1. Fetch articles from AskNews (with retry)
    2. Transform to storage format
    3. Batch insert with deduplication
    4. Continue to next entity even if current entity fails

    Args:
        db_session: Database session for article storage

    Returns:
        Execution stats dict with keys:
            - job: Job name
            - started_at: Job start timestamp
            - completed_at: Job completion timestamp
            - duration_seconds: Total execution time
            - entities_processed: Number of entities successfully processed
            - entities_failed: Number of entities that failed
            - total_articles_fetched: Total articles fetched across all entities
            - total_articles_inserted: Total articles inserted (after dedup)
            - errors: List of error dicts with entity and error message
    """
    start_time = datetime.utcnow()
    logger.info("news_job_started", entities=ENTITY_NAMES)

    # Initialize AskNews client
    try:
        client = AskNewsClient()
    except ValueError as exc:
        logger.error("news_job_failed", reason="asknews_client_init_failed", error=str(exc))
        return {
            "job": "poll_news",
            "started_at": start_time.isoformat(),
            "completed_at": datetime.utcnow().isoformat(),
            "duration_seconds": 0,
            "entities_processed": 0,
            "entities_failed": len(ENTITY_NAMES),
            "total_articles_fetched": 0,
            "total_articles_inserted": 0,
            "errors": [{"entity": "ALL", "error": str(exc)}]
        }

    # Execution tracking
    entities_processed = 0
    entities_failed = 0
    total_articles_fetched = 0
    total_articles_inserted = 0
    errors = []

    # Process each entity independently
    for entity_name in ENTITY_NAMES:
        try:
            # Fetch articles with retry
            articles = await fetch_from_asknews_with_retry(entity_name, client)
            total_articles_fetched += len(articles)

            if not articles:
                logger.info("no_articles_for_entity", entity=entity_name)
                entities_processed += 1
                continue

            # Transform to storage format
            storage_articles = []
            for article in articles:
                # Parse published_at from ISO string to datetime
                published_at = article.get('published_at')
                if isinstance(published_at, str):
                    try:
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        # Fallback to current time if parsing fails
                        published_at = datetime.utcnow()

                # Transform sentiment from int to score
                # AskNews returns sentiment as int: -1 (negative), 0 (neutral), 1 (positive)
                # Our schema expects float in -1 to 1 range
                sentiment = article.get('sentiment')
                if isinstance(sentiment, (int, float)):
                    sentiment_score = float(sentiment)
                else:
                    sentiment_score = 0.0  # Default to neutral

                storage_articles.append({
                    'external_id': article.get('external_id'),
                    'title': article.get('title'),
                    'url': article.get('url'),
                    'source_name': article.get('source_url'),
                    'published_at': published_at,
                    'sentiment_score': sentiment_score,
                    'entity': entity_name,  # For normalization in storage service
                })

            # Batch insert with deduplication
            inserted_count = await batch_insert_articles(storage_articles, db_session)
            total_articles_inserted += inserted_count

            entities_processed += 1
            logger.info(
                "entity_processed",
                entity=entity_name,
                fetched=len(articles),
                inserted=inserted_count
            )

        except Exception as exc:
            # Log error but continue with next entity
            entities_failed += 1
            error_msg = str(exc)
            errors.append({"entity": entity_name, "error": error_msg})
            logger.error(
                "entity_processing_failed",
                entity=entity_name,
                error=error_msg,
                exc_info=True
            )
            continue

    # Job completion
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    stats = {
        "job": "poll_news",
        "started_at": start_time.isoformat(),
        "completed_at": end_time.isoformat(),
        "duration_seconds": duration,
        "entities_processed": entities_processed,
        "entities_failed": entities_failed,
        "total_articles_fetched": total_articles_fetched,
        "total_articles_inserted": total_articles_inserted,
        "errors": errors
    }

    logger.info(
        "news_job_complete",
        **{k: v for k, v in stats.items() if k != "errors"}
    )

    return stats
