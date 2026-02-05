"""Article deduplication service using external_id and URL hash.

Primary deduplication uses external_id (AskNews article ID).
Secondary deduplication uses SHA256 hash of URL for articles with different external_ids.
"""
import hashlib
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Article

logger = structlog.get_logger(__name__)


def compute_url_hash(url: str) -> str:
    """Compute SHA256 hash of URL for deduplication.

    Args:
        url: Article URL to hash

    Returns:
        64-character hexadecimal hash string
    """
    return hashlib.sha256(url.encode('utf-8')).hexdigest()


async def check_article_exists(
    external_id: str,
    url: str,
    db_session: AsyncSession
) -> bool:
    """Check if article already exists using external_id or URL hash.

    Primary check: external_id (unique identifier from AskNews)
    Secondary check: url_hash (handles articles with different external_ids)

    Args:
        external_id: AskNews article identifier
        url: Article URL
        db_session: Database session

    Returns:
        True if article exists (duplicate), False otherwise
    """
    # Check external_id first (most reliable)
    stmt = select(Article.id).where(Article.external_id == external_id).limit(1)
    result = await db_session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        logger.debug("duplicate_found_by_external_id", external_id=external_id)
        return True

    # Check URL hash as secondary check
    url_hash = compute_url_hash(url)
    stmt = select(Article.id).where(Article.url_hash == url_hash).limit(1)
    result = await db_session.execute(stmt)
    if result.scalar_one_or_none() is not None:
        logger.debug("duplicate_found_by_url_hash", url=url, url_hash=url_hash)
        return True

    return False


async def batch_check_duplicates(
    articles: list[dict],
    db_session: AsyncSession
) -> tuple[list[dict], int]:
    """Filter out duplicate articles from batch.

    Args:
        articles: List of article dicts with 'external_id' and 'url' keys
        db_session: Database session

    Returns:
        Tuple of (articles_to_insert, duplicates_skipped_count)
    """
    to_insert = []
    duplicates_skipped = 0

    for article in articles:
        is_duplicate = await check_article_exists(
            external_id=article['external_id'],
            url=article['url'],
            db_session=db_session
        )

        if is_duplicate:
            duplicates_skipped += 1
        else:
            to_insert.append(article)

    logger.info(
        "batch_deduplication_complete",
        total=len(articles),
        to_insert=len(to_insert),
        duplicates_skipped=duplicates_skipped
    )

    return to_insert, duplicates_skipped
