"""Story polling job with sentiment time-series and Reddit extraction.

Fetches story clusters from AskNews /stories endpoint every 60 minutes (scheduled in Plan 04).
Extracts overall sentiment trends and Reddit-specific sentiment for community opinion tracking.

Job execution:
- Polls all 10 curated entities in parallel
- Retries failed entity fetches with exponential backoff
- Continues on per-entity failures to maximize data collection
- Stores sentiment time-series aggregates with Reddit metadata
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Entity
from pipeline.clients.asknews_client import AskNewsClient
from pipeline.services.sentiment_service import extract_story_sentiment, store_sentiment_timeseries
from utils.constants import CURATED_ENTITIES

logger = structlog.get_logger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutError, ConnectionError)),
    reraise=True,
)
async def fetch_stories_from_asknews_with_retry(
    entity_name: str,
    client: AskNewsClient,
) -> list[dict[str, Any]]:
    """Fetch stories for an entity with exponential backoff retry.

    Args:
        entity_name: Canonical entity name (e.g., 'GPT-4o', 'Claude').
        client: Initialized AskNewsClient instance.

    Returns:
        List of story dicts from AskNews API.

    Raises:
        TimeoutError, ConnectionError: On network failures (triggers retry).
        Exception: On API errors after max retries exhausted.

    Note:
        Retries only on transient network errors, not API validation errors.
    """
    logger.debug("fetching_stories_with_retry", entity=entity_name)
    stories = await client.fetch_stories(entity_name=entity_name, limit=10)
    return stories


async def poll_stories_job(db_session: AsyncSession) -> dict[str, Any]:
    """Poll AskNews stories endpoint for all curated entities.

    Main job execution logic:
    1. Initialize AskNews client
    2. For each curated entity:
       - Get entity_id from database
       - Fetch stories with retry
       - Extract sentiment time-series and Reddit data
       - Store aggregates in database
       - Track success/failure metrics
    3. Continue on per-entity failures to maximize data collection
    4. Return execution statistics

    Args:
        db_session: Async database session for entity lookup and storage.

    Returns:
        Dict with execution statistics:
            - total_entities: Number of entities processed
            - successful: Number of successful fetches
            - failed: Number of failed fetches
            - total_stories: Total stories fetched
            - stories_with_reddit: Stories containing Reddit data
            - stories_without_reddit: Stories missing Reddit data
            - timeseries_points_stored: Total time-series points stored
            - execution_time: Job duration in seconds

    Note:
        First story response is logged at INFO level for API validation.
    """
    start_time = datetime.utcnow()
    stats = {
        "total_entities": len(CURATED_ENTITIES),
        "successful": 0,
        "failed": 0,
        "total_stories": 0,
        "stories_with_reddit": 0,
        "stories_without_reddit": 0,
        "timeseries_points_stored": 0,
        "execution_time": 0.0,
    }

    logger.info("stories_job_started", entity_count=len(CURATED_ENTITIES))

    # Initialize AskNews client
    try:
        client = AskNewsClient()
    except ValueError as exc:
        logger.error("asknews_client_init_failed", error=str(exc))
        stats["failed"] = len(CURATED_ENTITIES)
        return stats

    # Process each entity
    first_story_logged = False
    for entity_config in CURATED_ENTITIES:
        entity_name = entity_config["name"]

        try:
            # Get entity_id from database
            stmt = select(Entity).where(Entity.name == entity_name)
            result = await db_session.execute(stmt)
            entity = result.scalar_one_or_none()

            if not entity:
                logger.warning(
                    "entity_not_found_in_database",
                    entity=entity_name,
                    hint="Run entity seeding script to populate Entity table",
                )
                stats["failed"] += 1
                continue

            entity_id = entity.id

            # Fetch stories with retry
            try:
                stories = await fetch_stories_from_asknews_with_retry(
                    entity_name=entity_name,
                    client=client,
                )
            except Exception as fetch_exc:
                logger.error(
                    "story_fetch_failed_after_retries",
                    entity=entity_name,
                    error=str(fetch_exc),
                )
                stats["failed"] += 1
                continue  # Continue to next entity

            stats["successful"] += 1
            stats["total_stories"] += len(stories)

            # Log first story response for API validation
            if stories and not first_story_logged:
                logger.info(
                    "first_story_response_sample",
                    entity=entity_name,
                    story_count=len(stories),
                    sample_story=str(stories[0])[:1000],  # First 1000 chars
                )
                first_story_logged = True

            # Process each story
            for story in stories:
                try:
                    # Extract sentiment and Reddit data
                    sentiment_data = extract_story_sentiment(story)

                    # Track Reddit statistics
                    if sentiment_data["has_reddit"]:
                        stats["stories_with_reddit"] += 1
                    else:
                        stats["stories_without_reddit"] += 1

                    # Store time-series points
                    for point in sentiment_data["timeseries"]:
                        stored = await store_sentiment_timeseries(
                            entity_id=entity_id,
                            timestamp=point["timestamp"],
                            sentiment_mean=point["sentiment_mean"],
                            article_count=point.get("article_count"),
                            reddit_sentiment=sentiment_data["reddit_sentiment"],
                            reddit_thread_count=sentiment_data["reddit_thread_count"],
                            period="hourly",
                            source="stories",
                            db_session=db_session,
                        )
                        if stored:
                            stats["timeseries_points_stored"] += 1

                except Exception as story_exc:
                    logger.error(
                        "story_processing_failed",
                        entity=entity_name,
                        story_id=story.get("story_id", "unknown"),
                        error=str(story_exc),
                        exc_info=True,
                    )
                    # Continue to next story

        except Exception as entity_exc:
            logger.error(
                "entity_processing_failed",
                entity=entity_name,
                error=str(entity_exc),
                exc_info=True,
            )
            stats["failed"] += 1
            continue  # Continue to next entity

    # Calculate execution time
    end_time = datetime.utcnow()
    stats["execution_time"] = (end_time - start_time).total_seconds()

    logger.info(
        "stories_job_completed",
        **stats,
    )

    return stats
