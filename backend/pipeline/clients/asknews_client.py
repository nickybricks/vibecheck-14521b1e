"""AskNews SDK client wrapper with async methods for news and stories.

This module provides an async interface to AskNews API endpoints for:
- News Search: Individual articles with sentiment analysis
- Story Clustering: Aggregated story clusters with time-series sentiment

Authentication uses API key (simpler than OAuth2 client credentials flow).
"""

import os
from datetime import datetime
from typing import Any

import httpx
import structlog
from asknews_sdk import AsyncAskNewsSDK

logger = structlog.get_logger(__name__)


class APIKeyAuth(httpx.Auth):
    """httpx authentication for API key (Bearer token)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def auth_flow(self, request: httpx.Request):
        """Inject API key as Bearer token into request headers."""
        request.headers["Authorization"] = f"Bearer {self.api_key}"
        yield request


class AskNewsClient:
    """Async wrapper for AskNews SDK.

    Provides API key authenticated access to news and stories endpoints
    with structured logging and standard dict response formats.
    """

    def __init__(self):
        """Initialize AskNews SDK client with API key from environment.

        Uses API key authentication (simpler than OAuth2 client credentials).

        Raises:
            ValueError: If ASKNEWS_API_KEY environment variable is missing.
        """
        api_key = os.getenv("ASKNEWS_API_KEY")
        if not api_key:
            raise ValueError("ASKNEWS_API_KEY environment variable is required")

        # Initialize SDK with API key authentication
        # Pass auth=None to disable default OAuth2 flow, then set custom auth
        self.client = AsyncAskNewsSDK(
            client_id=None,  # Not needed for API key auth
            client_secret=None,  # Not needed for API key auth
            auth=APIKeyAuth(api_key),  # Custom API key auth
            scopes=set(),  # Empty set for API key auth
        )
        logger.info("asknews_client_initialized", auth_method="api_key")

    async def fetch_news(self, entity_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch news articles for an entity from AskNews News Search endpoint.

        Args:
            entity_name: Canonical entity name to search for.
            limit: Maximum number of articles to return (default: 10).

        Returns:
            List of article dicts with keys:
                - external_id: AskNews article ID
                - title: Article headline
                - entity_name: Entity this article relates to
                - sentiment: Sentiment score (positive/negative/neutral or numeric)
                - url: Article URL
                - source_url: Source domain
                - published_at: ISO 8601 timestamp

        Raises:
            Exception: On API errors (propagates exceptions for retry handling).
        """
        try:
            logger.debug("fetching_news", entity=entity_name, limit=limit)

            # Call AskNews SDK news search
            # n_articles: max number of articles
            # string_guarantee: ensures entity appears in results
            # return_type='dicts': returns list of dicts instead of string
            response = await self.client.news.search_news(
                query=entity_name,
                n_articles=limit,
                string_guarantee=[entity_name],
                return_type="dicts"
            )

            # Transform SDK response to standard dict format
            # response.as_dicts returns list of Pydantic models
            articles = []
            for item in response.as_dicts:
                article = {
                    "external_id": str(item.article_id) if item.article_id else None,
                    "title": item.title,
                    "entity_name": entity_name,
                    "sentiment": item.sentiment,  # int value
                    "url": str(item.article_url) if item.article_url else None,
                    "source_url": str(item.domain_url) if item.domain_url else None,
                    "published_at": item.pub_date.isoformat() if item.pub_date else None,
                }
                articles.append(article)

            logger.info(
                "asknews_news_fetched",
                entity=entity_name,
                count=len(articles)
            )
            return articles

        except Exception as exc:
            logger.error(
                "asknews_news_fetch_failed",
                entity=entity_name,
                error=str(exc),
                exc_info=True
            )
            raise  # Propagate for retry handling in jobs

    async def fetch_stories(self, entity_name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch story clusters for an entity from AskNews Stories endpoint.

        Stories aggregate multiple articles into clusters with time-series sentiment.

        Args:
            entity_name: Canonical entity name to search for.
            limit: Maximum number of stories to return (default: 10).

        Returns:
            List of story dicts with keys:
                - story_id: AskNews story cluster UUID
                - entity_name: Entity this story relates to
                - headline: Story headline/topic
                - sentiment_timeseries: List of time-series sentiment points
                - reddit_sentiment_timeseries: List of Reddit-specific sentiment points
                - reddit_threads: List of related Reddit discussion threads

        Raises:
            Exception: On API errors (propagates exceptions for retry handling).

        Note:
            First call will log full response structure for validation of schema.
        """
        try:
            logger.debug("fetching_stories", entity=entity_name, limit=limit)

            # Call AskNews SDK stories search
            response = await self.client.stories.search_stories(
                query=entity_name,
                limit=limit
            )

            # Transform SDK response to standard dict format
            stories = []
            for story in response.stories:
                # Build sentiment time series from parallel arrays
                sentiment_timeseries = [
                    {"timestamp": ts, "score": score}
                    for ts, score in zip(story.sentiment_timestamps, story.sentiment)
                ]

                # Build Reddit sentiment time series
                reddit_sentiment_timeseries = [
                    {"timestamp": ts, "score": score}
                    for ts, score in zip(story.reddit_sentiment_timestamps, story.reddit_sentiment)
                ]

                # Extract Reddit threads from the latest update (if available)
                reddit_threads = []
                if story.updates:
                    latest_update = story.updates[0]  # Most recent update
                    # Convert RedditThread objects to dicts
                    reddit_threads = [
                        {
                            "thread_id": str(thread.id),
                            "title": thread.title,
                            "url": thread.url,
                            "subreddit": thread.subreddit_name,
                            "upvotes": thread.upvotes,
                            "sentiment": thread.sentiment,
                            "date": thread.date.isoformat() if thread.date else None,
                        }
                        for thread in (latest_update.reddit_threads or [])
                    ]

                story_dict = {
                    "story_id": str(story.uuid),
                    "entity_name": entity_name,
                    "headline": story.topic,
                    "sentiment_timeseries": sentiment_timeseries,
                    "reddit_sentiment_timeseries": reddit_sentiment_timeseries,
                    "reddit_threads": reddit_threads,
                }
                stories.append(story_dict)

            logger.info(
                "asknews_stories_fetched",
                entity=entity_name,
                count=len(stories)
            )
            return stories

        except Exception as exc:
            logger.error(
                "asknews_stories_fetch_failed",
                entity=entity_name,
                error=str(exc),
                exc_info=True
            )
            raise  # Propagate for retry handling in jobs
