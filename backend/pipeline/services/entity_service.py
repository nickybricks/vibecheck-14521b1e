"""Entity normalization service for mapping name variations to canonical entities.

Handles entity name variations from news sources and API responses,
normalizing them to canonical entity names for consistent tracking.
"""

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Entity
from utils.constants import ENTITY_VARIATIONS

logger = structlog.get_logger(__name__)


def normalize_entity_name(extracted_name: str) -> str | None:
    """Normalize an entity name variation to its canonical name.

    Uses bidirectional substring matching to handle partial matches and
    common variations (e.g., "OpenAI's GPT-4o" -> "GPT-4o").

    Args:
        extracted_name: Raw entity name from news article or API response.

    Returns:
        Canonical entity name if match found, None for non-curated entities.

    Examples:
        >>> normalize_entity_name("OpenAI GPT-4o")
        "GPT-4o"
        >>> normalize_entity_name("Claude 3.5 Sonnet")
        "Claude"
        >>> normalize_entity_name("Unknown Model")
        None
    """
    # Normalize for case-insensitive matching
    normalized = extracted_name.strip().lower()

    # Check each canonical entity and its variations
    for canonical_name, variations in ENTITY_VARIATIONS.items():
        # Check exact match with canonical name
        if normalized == canonical_name.lower():
            logger.debug(
                "entity_normalized_exact",
                extracted=extracted_name,
                canonical=canonical_name
            )
            return canonical_name

        # Check variations with bidirectional substring matching
        for variation in variations:
            variation_lower = variation.lower()
            # Bidirectional: either one contains the other
            if variation_lower in normalized or normalized in variation_lower:
                logger.debug(
                    "entity_normalized_variation",
                    extracted=extracted_name,
                    matched_variation=variation,
                    canonical=canonical_name
                )
                return canonical_name

    # No match found - not a curated entity
    logger.info(
        "entity_not_recognized",
        extracted=extracted_name,
        reason="not_in_curated_list"
    )
    return None


async def get_entity_id_by_name(
    canonical_name: str,
    db_session: AsyncSession
) -> int | None:
    """Get entity database ID by canonical name.

    Args:
        canonical_name: Canonical entity name (must match Entity.name exactly).
        db_session: Async database session.

    Returns:
        Entity ID if found, None if not in database.

    Note:
        Assumes entities are pre-seeded in database during migration/initialization.
    """
    try:
        stmt = select(Entity).where(Entity.name == canonical_name)
        result = await db_session.execute(stmt)
        entity = result.scalar_one_or_none()

        if entity:
            logger.debug(
                "entity_id_resolved",
                name=canonical_name,
                id=entity.id
            )
            return entity.id
        else:
            logger.warning(
                "entity_not_in_database",
                name=canonical_name,
                hint="run entity seeding script"
            )
            return None

    except Exception as exc:
        logger.error(
            "entity_id_lookup_failed",
            name=canonical_name,
            error=str(exc),
            exc_info=True
        )
        return None
