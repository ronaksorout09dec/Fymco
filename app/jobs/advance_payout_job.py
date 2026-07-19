import asyncio
import logging

from app.db.session import SessionLocal
from app.services import AdvanceService

logger = logging.getLogger(__name__)


async def run_advance_payout_job() -> int:
    """One retry-safe job invocation, callable by the scheduler or an operator."""
    async with SessionLocal() as session:
        payouts = await AdvanceService(session).process_pending_sales()
        logger.info("advance_job_completed", extra={"processed": len(payouts)})
        return len(payouts)


if __name__ == "__main__":
    asyncio.run(run_advance_payout_job())
