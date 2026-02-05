"""Article storage service for batch insertion with deduplication and normalization.

Handles batch insertion of articles with entity name normalization and
deduplication checks before database writes.
"""
import structlog
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article
from pipeline.services.deduplication_service import batch_check_duplicates, compute_url_hash
from pipeline.services.entity_service import normalize_entity_name

logger = structlog.get_logger(__name__)


async def batch_insert_articles(
    articles: list[dict],
    db_session: AsyncSession
) -> int:
    """Batch insert articles with deduplication and entity normalization.

    Pipeline:
    1. Filter duplicates via batch_check_duplicates
    2. Normalize entity names to canonical form
    3. Compute URL hash for each article
    4. Batch insert into database

    Args:
        articles: List of article dicts with keys:
            - external_id: AskNews article ID
            - title: Article title
            - url: Article URL
            - source_name: News source (optional)
            - published_at: Publication datetime
            - sentiment_score: Sentiment score (optional)
            - entity: Raw entity name to normalize
        db_session: Database session

    Returns:
        Count of articles inserted

    Note:
        Articles with non-curated entities (normalize_entity_name returns None)
        are silently skipped. This is expected behavior for filtering.
    """
    if not articles:
        logger.info("batch_insert_skipped", reason="empty_list")
        return 0

    # Step 1: Filter duplicates
    to_insert, duplicates_skipped = await batch_check_duplicates(articles, db_session)

    if not to_insert:
        logger.info(
            "batch_insert_complete",
            total=len(articles),
            inserted=0,
            duplicates_skipped=duplicates_skipped,
            non_curated_skipped=0
        )
        return 0

    # Step 2-3: Normalize entities and prepare for insertion
    normalized_articles = []
    non_curated_skipped = 0

    for article in to_insert:
        # Normalize entity name
        canonical_name = normalize_entity_name(article.get('entity', ''))

        if canonical_name is None:
            # Skip articles for non-curated entities
            non_curated_skipped += 1
            continue

        # Compute URL hash
        url_hash = compute_url_hash(article['url'])

        # Prepare Article model instance
        normalized_articles.append(
            Article(
                external_id=article['external_id'],
                title=article['title'],
                url=article['url'],
                url_hash=url_hash,
                source_name=article.get('source_name'),
                published_at=article['published_at'],
                sentiment_score=article.get('sentiment_score'),
                created_at=datetime.utcnow()
            )
        )

    # Step 4: Batch insert
    if normalized_articles:
        db_session.add_all(normalized_articles)
        await db_session.commit()

    inserted_count = len(normalized_articles)

    logger.info(
        "batch_insert_complete",
        total=len(articles),
        inserted=inserted_count,
        duplicates_skipped=duplicates_skipped,
        non_curated_skipped=non_curated_skipped
    )

    return inserted_count
