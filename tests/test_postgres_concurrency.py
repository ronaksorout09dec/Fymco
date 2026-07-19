import asyncio
import os
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.entities import Withdrawal
from app.models.enums import SaleStatus
from app.services import AdvanceService, DirectoryService, ReconciliationService, SalesService, WithdrawalService

POSTGRES_URL = os.getenv("POSTGRES_INTEGRATION_URL")
IS_DISPOSABLE_TEST_DATABASE = bool(POSTGRES_URL and "test" in POSTGRES_URL.lower())


@pytest.mark.postgres
@pytest.mark.asyncio
@pytest.mark.skipif(
    not IS_DISPOSABLE_TEST_DATABASE,
    reason="Set POSTGRES_INTEGRATION_URL to a disposable database whose URL contains 'test'",
)
async def test_concurrent_idempotent_withdrawals_create_one_debit():
    engine = create_async_engine(POSTGRES_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    try:
        async with factory() as setup_session:
            directory = DirectoryService(setup_session)
            user = await directory.create_user("concurrent-user")
            brand = await directory.create_brand("concurrent-brand")
            sale = await SalesService(setup_session).create_sale(user.id, brand.id, Decimal("100"))
            await AdvanceService(setup_session).process_pending_sales()
            await ReconciliationService(setup_session).reconcile_sale(sale.id, SaleStatus.APPROVED)

        async def request_once():
            async with factory() as request_session:
                return await WithdrawalService(request_session).initiate_withdrawal(
                    user.id, Decimal("90"), "shared-idempotency-key"
                )

        first, second = await asyncio.gather(request_once(), request_once())
        assert first.id == second.id
        async with factory() as verification_session:
            count = await verification_session.scalar(select(func.count()).select_from(Withdrawal))
        assert count == 1
    finally:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
        await engine.dispose()
