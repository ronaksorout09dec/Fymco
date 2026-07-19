import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import get_settings
from app.jobs.advance_payout_job import run_advance_payout_job

logger = logging.getLogger(__name__)


def start_scheduler() -> AsyncIOScheduler | None:
    settings = get_settings()
    if not settings.advance_job_enabled:
        return None
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_advance_payout_job,
        trigger=CronTrigger.from_crontab(settings.advance_job_cron, timezone="UTC"),
        id="advance-payouts",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("advance_scheduler_started")
    return scheduler
