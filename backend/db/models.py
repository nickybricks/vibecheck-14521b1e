"""SQLAlchemy ORM models for VibeCheck entities, articles, and sentiment time-series.

Models follow TimescaleDB-compatible schema design for efficient time-series queries.
All timestamps use TIMESTAMP WITH TIME ZONE stored in UTC.
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, Float, TIMESTAMP, CheckConstraint, ForeignKey, Index, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.base import Base


class Entity(Base):
    """AI models and tools tracked for sentiment analysis.

    Entities are the subjects of sentiment tracking (e.g., 'GPT-4', 'Claude', 'LangChain').
    """
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # "model" or "tool"
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )


class Article(Base):
    """News articles and Reddit posts with sentiment scores.

    Stores raw article metadata and individual sentiment scores from AskNews API.
    """
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True
    )
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "sentiment_score >= -1 AND sentiment_score <= 1",
            name="ck_article_sentiment_score_range"
        ),
    )


class SentimentTimeseries(Base):
    """Pre-computed sentiment aggregates for time-series queries.

    Stores hourly and daily sentiment statistics per entity for efficient charting.
    TimescaleDB-compatible schema with composite index on (entity_id, timestamp DESC).
    """
    __tablename__ = "sentiment_timeseries"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(
        ForeignKey("entities.id"),
        nullable=False,
        index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True
    )
    period: Mapped[str] = mapped_column(String(10), nullable=False)  # "hourly" or "daily"
    sentiment_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    article_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reddit_sentiment: Mapped[float | None] = mapped_column(Float, nullable=True)
    reddit_thread_count: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        Index(
            "ix_sentiment_timeseries_entity_timestamp",
            "entity_id",
            "timestamp",
            postgresql_ops={"timestamp": "DESC"}
        ),
        CheckConstraint(
            "sentiment_mean >= -1 AND sentiment_mean <= 1",
            name="ck_sentiment_timeseries_mean_range"
        ),
        CheckConstraint(
            "sentiment_min >= -1 AND sentiment_min <= 1",
            name="ck_sentiment_timeseries_min_range"
        ),
        CheckConstraint(
            "sentiment_max >= -1 AND sentiment_max <= 1",
            name="ck_sentiment_timeseries_max_range"
        ),
    )


class SchedulerExecutionLog(Base):
    """Audit trail for scheduled job executions.

    Records every job execution with timing, status, and error tracking
    for monitoring silent failures and performance issues.
    """
    __tablename__ = "scheduler_execution_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False
    )
