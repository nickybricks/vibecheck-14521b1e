"""APScheduler integration for automated news and story polling.

Manages scheduled job execution with health monitoring and audit logging.
Jobs run on fixed intervals: news every 15 minutes, stories every 60 minutes.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from db.models import SchedulerExecutionLog
from pipeline.jobs.news_job import poll_news_job
from pipeline.jobs.stories_job import poll_stories_job

logger = structlog.get_logger(__name__)

# Module-level scheduler instance
scheduler = AsyncIOScheduler(timezone='UTC')

# Track last successful run time for health checks
job_last_run: dict[str, datetime] = {}


async def wrapped_job_execution(
    job_name: str,
    job_func: Callable[[AsyncSession], dict[str, Any]],
    db_session: AsyncSession
) -> None:
    """Execute job with audit logging and error handling.

    Wraps job execution to:
    - Generate unique execution_id for tracing
    - Log start/completion to SchedulerExecutionLog table
    - Capture errors without crashing scheduler
    - Track last successful run time for health monitoring
    - Store job execution metadata (stats returned by job)

    Args:
        job_name: Identifier for the job (e.g., 'poll_news', 'poll_stories')
        job_func: Async function that executes the job logic
        db_session: Database session for logging and job execution

    Returns:
        None (logs results to database)
    """
    execution_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    logger.info("job_execution_started", job_name=job_name, execution_id=execution_id)

    # Create execution log entry
    log_entry = SchedulerExecutionLog(
        execution_id=execution_id,
        job_name=job_name,
        status="running",
        started_at=started_at,
        completed_at=None,
        duration_seconds=None,
        error_message=None,
        metadata_json=None,
    )
    db_session.add(log_entry)
    await db_session.commit()

    try:
        # Execute job
        job_stats = await job_func(db_session)

        # Job completed successfully
        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - started_at).total_seconds()

        log_entry.status = "success"
        log_entry.completed_at = completed_at
        log_entry.duration_seconds = duration
        log_entry.metadata_json = job_stats

        await db_session.commit()

        # Update health tracking
        job_last_run[job_name] = completed_at

        logger.info(
            "job_execution_completed",
            job_name=job_name,
            execution_id=execution_id,
            duration_seconds=duration,
        )

    except Exception as exc:
        # Job failed - log error but don't crash scheduler
        completed_at = datetime.now(timezone.utc)
        duration = (completed_at - started_at).total_seconds()

        log_entry.status = "failed"
        log_entry.completed_at = completed_at
        log_entry.duration_seconds = duration
        log_entry.error_message = str(exc)

        await db_session.commit()

        logger.error(
            "job_execution_failed",
            job_name=job_name,
            execution_id=execution_id,
            error=str(exc),
            exc_info=True,
        )


async def poll_news_job_wrapper() -> None:
    """Wrapper for news polling job with database session management.

    Gets database session and executes poll_news_job with audit logging.
    """
    async for session in get_session():
        try:
            await wrapped_job_execution("poll_news", poll_news_job, session)
        finally:
            await session.close()
        break  # get_session is a generator, only need first yield


async def poll_stories_job_wrapper() -> None:
    """Wrapper for stories polling job with database session management.

    Gets database session and executes poll_stories_job with audit logging.
    """
    async for session in get_session():
        try:
            await wrapped_job_execution("poll_stories", poll_stories_job, session)
        finally:
            await session.close()
        break  # get_session is a generator, only need first yield


def setup_jobs() -> None:
    """Register scheduled jobs with APScheduler.

    Jobs registered:
    - poll_news: Every 15 minutes (for high-frequency news tracking)
    - poll_stories: Every 60 minutes (for story clustering with Reddit sentiment)

    Jobs use IntervalTrigger for fixed-interval execution.
    Scheduler must be started separately via scheduler.start().
    """
    # News job - every 15 minutes
    scheduler.add_job(
        poll_news_job_wrapper,
        trigger='interval',
        minutes=15,
        id='poll_news',
        name='Poll AskNews for news articles',
        replace_existing=True,
    )

    # Stories job - every 60 minutes
    scheduler.add_job(
        poll_stories_job_wrapper,
        trigger='interval',
        minutes=60,
        id='poll_stories',
        name='Poll AskNews for story clusters',
        replace_existing=True,
    )

    logger.info("scheduler_jobs_registered", job_count=len(scheduler.get_jobs()))


async def get_job_health() -> dict[str, Any]:
    """Get health status for all scheduled jobs.

    Returns job last run times and alerts if jobs are overdue.
    A job is considered overdue if it hasn't run in 2x its scheduled interval.

    Returns:
        Dict with structure:
        {
            "healthy": bool,  # True if all jobs running on schedule
            "jobs": {
                "poll_news": {
                    "last_run": "2026-02-05T12:30:00Z" or None,
                    "interval_minutes": 15,
                    "overdue": bool,
                    "minutes_since_last_run": float or None
                },
                "poll_stories": {...}
            }
        }
    """
    now = datetime.now(timezone.utc)
    job_configs = {
        "poll_news": {"interval_minutes": 15},
        "poll_stories": {"interval_minutes": 60},
    }

    jobs_status = {}
    all_healthy = True

    for job_name, config in job_configs.items():
        last_run = job_last_run.get(job_name)
        interval_minutes = config["interval_minutes"]

        if last_run is None:
            # Job hasn't run yet
            jobs_status[job_name] = {
                "last_run": None,
                "interval_minutes": interval_minutes,
                "overdue": False,  # Can't be overdue if never run
                "minutes_since_last_run": None,
            }
        else:
            # Calculate time since last run
            time_since_run = (now - last_run).total_seconds() / 60  # minutes
            overdue = time_since_run > (interval_minutes * 2)

            jobs_status[job_name] = {
                "last_run": last_run.isoformat(),
                "interval_minutes": interval_minutes,
                "overdue": overdue,
                "minutes_since_last_run": round(time_since_run, 2),
            }

            if overdue:
                all_healthy = False

    return {
        "healthy": all_healthy,
        "jobs": jobs_status,
    }
