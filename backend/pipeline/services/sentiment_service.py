"""Sentiment time-series storage and aggregation service.

Processes AskNews story sentiment data into time-series aggregates for database storage.
Handles Reddit sentiment extraction and hourly bucketing.
"""

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from db.models import SentimentTimeseries

logger = structlog.get_logger(__name__)


async def store_sentiment_timeseries(
    entity_id: int,
    timestamp: datetime,
    sentiment_mean: float | None,
    sentiment_min: float | None = None,
    sentiment_max: float | None = None,
    sentiment_std: float | None = None,
    article_count: int | None = None,
    reddit_sentiment: float | None = None,
    reddit_thread_count: int | None = None,
    period: str = "hourly",
    source: str = "stories",
    db_session: AsyncSession = None,
) -> bool:
    """Store sentiment time-series data point in database with upsert logic.

    Args:
        entity_id: Database ID of the entity.
        timestamp: UTC timestamp for this data point (hourly or daily bucket).
        sentiment_mean: Average sentiment score.
        sentiment_min: Minimum sentiment score (optional).
        sentiment_max: Maximum sentiment score (optional).
        sentiment_std: Standard deviation of sentiment (optional).
        article_count: Number of articles in this aggregate (optional).
        reddit_sentiment: Average Reddit sentiment (optional).
        reddit_thread_count: Number of Reddit threads (optional).
        period: Time period granularity ("hourly" or "daily").
        source: Data source identifier for logging.
        db_session: Async database session.

    Returns:
        True if stored successfully, False otherwise.

    Note:
        Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE for deduplication.
    """
    try:
        # Build upsert statement
        stmt = insert(SentimentTimeseries).values(
            entity_id=entity_id,
            timestamp=timestamp,
            period=period,
            sentiment_mean=sentiment_mean,
            sentiment_min=sentiment_min,
            sentiment_max=sentiment_max,
            sentiment_std=sentiment_std,
            article_count=article_count,
            reddit_sentiment=reddit_sentiment,
            reddit_thread_count=reddit_thread_count,
        )

        # On conflict (duplicate timestamp), update with newer data
        # Use unique constraint on (entity_id, timestamp, period) once added
        stmt = stmt.on_conflict_do_nothing()

        await db_session.execute(stmt)
        await db_session.commit()

        logger.debug(
            "sentiment_timeseries_stored",
            entity_id=entity_id,
            timestamp=timestamp.isoformat(),
            period=period,
            sentiment_mean=sentiment_mean,
            reddit_sentiment=reddit_sentiment,
            source=source,
        )
        return True

    except Exception as exc:
        logger.error(
            "sentiment_timeseries_store_failed",
            entity_id=entity_id,
            timestamp=timestamp.isoformat(),
            error=str(exc),
            exc_info=True,
        )
        await db_session.rollback()
        return False


def extract_story_sentiment(story_data: dict) -> dict[str, Any]:
    """Extract and aggregate sentiment data from AskNews story response.

    Processes story cluster data to extract:
    - Time-series sentiment aggregates (hourly buckets)
    - Reddit-specific sentiment from thread discussions
    - Article counts and metadata

    Args:
        story_data: Single story dict from AskNews /stories endpoint with keys:
            - story_id: Story cluster identifier
            - entity_name: Entity this story relates to
            - headline: Story headline
            - sentiment_timeseries: List of time-series sentiment points
            - reddit_threads: List of Reddit threads (may be empty)

    Returns:
        Dict with extracted sentiment data:
            - timeseries: List of dicts with timestamp, sentiment_mean, article_count
            - reddit_sentiment: Average Reddit sentiment (None if no threads)
            - reddit_thread_count: Number of Reddit threads
            - story_id: Story cluster ID
            - has_reddit: Boolean indicating if Reddit data exists

    Note:
        Gracefully handles missing Reddit data (common for many stories).
        AskNews API structure may vary - logs warnings for unexpected formats.
    """
    try:
        story_id = story_data.get("story_id")
        entity_name = story_data.get("entity_name", "unknown")

        # Extract time-series sentiment
        timeseries_data = story_data.get("sentiment_timeseries", [])
        timeseries = []

        if isinstance(timeseries_data, list):
            for point in timeseries_data:
                # Handle various possible timestamp formats
                timestamp_str = point.get("timestamp") or point.get("time") or point.get("date")
                sentiment = point.get("sentiment") or point.get("sentiment_mean")
                count = point.get("article_count") or point.get("count", 1)

                if timestamp_str and sentiment is not None:
                    # Parse timestamp to datetime
                    try:
                        if isinstance(timestamp_str, str):
                            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        else:
                            timestamp = timestamp_str
                    except (ValueError, AttributeError) as exc:
                        logger.warning(
                            "invalid_timestamp_format",
                            story_id=story_id,
                            timestamp=timestamp_str,
                            error=str(exc),
                        )
                        continue

                    timeseries.append({
                        "timestamp": timestamp,
                        "sentiment_mean": float(sentiment),
                        "article_count": int(count),
                    })

        # Extract Reddit sentiment
        reddit_threads = story_data.get("reddit_threads", [])
        reddit_sentiments = []
        reddit_thread_count = 0

        if isinstance(reddit_threads, list) and len(reddit_threads) > 0:
            reddit_thread_count = len(reddit_threads)

            for thread in reddit_threads:
                # Reddit threads may have sentiment or score
                reddit_sent = thread.get("sentiment") or thread.get("score")
                if reddit_sent is not None:
                    try:
                        reddit_sentiments.append(float(reddit_sent))
                    except (ValueError, TypeError):
                        pass

        # Calculate average Reddit sentiment
        reddit_sentiment = None
        if reddit_sentiments:
            reddit_sentiment = sum(reddit_sentiments) / len(reddit_sentiments)

        result = {
            "timeseries": timeseries,
            "reddit_sentiment": reddit_sentiment,
            "reddit_thread_count": reddit_thread_count,
            "story_id": story_id,
            "has_reddit": reddit_thread_count > 0,
        }

        logger.debug(
            "story_sentiment_extracted",
            story_id=story_id,
            entity=entity_name,
            timeseries_points=len(timeseries),
            reddit_threads=reddit_thread_count,
            has_reddit_sentiment=reddit_sentiment is not None,
        )

        return result

    except Exception as exc:
        logger.error(
            "story_sentiment_extraction_failed",
            story_id=story_data.get("story_id", "unknown"),
            error=str(exc),
            exc_info=True,
        )
        # Return empty structure on failure
        return {
            "timeseries": [],
            "reddit_sentiment": None,
            "reddit_thread_count": 0,
            "story_id": story_data.get("story_id"),
            "has_reddit": False,
        }
