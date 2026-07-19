from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from app.core.exceptions import BusinessRuleError, ConflictError
from app.models.entities import AdvancePayout, LedgerEntry, Withdrawal
from app.models.enums import SaleStatus, WithdrawalStatus
from app.services import AdvanceService, DirectoryService, ReconciliationService, SalesService, WithdrawalService
from app.repositories import SaleRepository


async def create_sale_with_directory(session, username: str, earning: str = "40.00"):
    directory = DirectoryService(session)
    user = await directory.create_user(username)
    brand = await directory.create_brand(f"brand-{username}")
    return user, await SalesService(session).create_sale(user.id, brand.id, Decimal(earning))


@pytest.mark.asyncio
async def test_create_sale_starts_pending(session):
    _, sale = await create_sale_with_directory(session, "pending-user")
    assert sale.status == SaleStatus.PENDING
    assert sale.earning == Decimal("40.00")


@pytest.mark.asyncio
async def test_advance_is_exactly_ten_percent_and_rerunnable(session):
    _, sale = await create_sale_with_directory(session, "advance-user", "35.55")
    first_run = await AdvanceService(session).process_pending_sales()
    second_run = await AdvanceService(session).process_pending_sales()
    count = await session.scalar(select(func.count()).select_from(AdvancePayout).where(AdvancePayout.sale_id == sale.id))
    assert first_run[0].amount == Decimal("3.56")
    assert second_run == []
    assert count == 1


def test_advance_query_locks_only_sales_on_postgresql():
    statement = SaleRepository.pending_without_advance_statement()
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE OF sales SKIP LOCKED" in sql


@pytest.mark.asyncio
async def test_reference_example_final_total_is_68(session):
    directory = DirectoryService(session)
    user = await directory.create_user("john_doe")
    brand = await directory.create_brand("brand_1")
    sales_service = SalesService(session)
    sales = [await sales_service.create_sale(user.id, brand.id, Decimal("40")) for _ in range(3)]
    advances = await AdvanceService(session).process_pending_sales()
    assert sum((payout.amount for payout in advances), Decimal("0")) == Decimal("12.00")
    reconciliation = ReconciliationService(session)
    await reconciliation.reconcile_sale(sales[0].id, SaleStatus.REJECTED)
    await reconciliation.reconcile_sale(sales[1].id, SaleStatus.APPROVED)
    await reconciliation.reconcile_sale(sales[2].id, SaleStatus.APPROVED)
    balance = await WithdrawalService(session).get_balance(user.id)
    assert balance.available_balance == Decimal("68.00")


@pytest.mark.asyncio
async def test_reconciliation_is_once_only_and_creates_one_ledger_entry(session):
    _, sale = await create_sale_with_directory(session, "reconcile-user")
    sale_id = sale.id
    await AdvanceService(session).process_pending_sales()
    reconciliation = ReconciliationService(session)
    await reconciliation.reconcile_sale(sale_id, SaleStatus.APPROVED)
    with pytest.raises(ConflictError):
        await reconciliation.reconcile_sale(sale_id, SaleStatus.REJECTED)
    entries = await session.scalar(select(func.count()).select_from(LedgerEntry).where(LedgerEntry.sale_id == sale_id))
    assert entries == 1


@pytest.mark.asyncio
async def test_withdrawal_failure_restores_balance_and_exact_retry_is_allowed(session):
    user, sale = await create_sale_with_directory(session, "withdrawal-user", "100")
    await AdvanceService(session).process_pending_sales()
    await ReconciliationService(session).reconcile_sale(sale.id, SaleStatus.APPROVED)
    service = WithdrawalService(session)
    withdrawal = await service.initiate_withdrawal(user.id, Decimal("90"), "withdraw-1")
    assert (await service.get_balance(user.id)).available_balance == Decimal("0.00")
    await service.apply_provider_status(withdrawal.id, "provider-event-1", WithdrawalStatus.FAILED, "provider-1")
    assert (await service.get_balance(user.id)).available_balance == Decimal("90.00")
    retry = await service.initiate_withdrawal(user.id, Decimal("90"), "withdraw-2", withdrawal.id)
    assert retry.retry_of_id == withdrawal.id
    with pytest.raises(BusinessRuleError):
        await service.initiate_withdrawal(user.id, Decimal("89"), "withdraw-3", withdrawal.id)


@pytest.mark.asyncio
async def test_withdrawal_idempotency_and_cooldown(session):
    user, sale = await create_sale_with_directory(session, "idempotency-user", "100")
    await AdvanceService(session).process_pending_sales()
    await ReconciliationService(session).reconcile_sale(sale.id, SaleStatus.APPROVED)
    service = WithdrawalService(session)
    first = await service.initiate_withdrawal(user.id, Decimal("50"), "same-key")
    duplicate = await service.initiate_withdrawal(user.id, Decimal("50"), "same-key")
    assert duplicate.id == first.id
    assert await session.scalar(select(func.count()).select_from(Withdrawal)) == 1
    with pytest.raises(BusinessRuleError, match="24-hour"):
        await service.initiate_withdrawal(user.id, Decimal("1"), "new-key")


@pytest.mark.asyncio
async def test_provider_callback_is_idempotent_and_does_not_double_restore(session):
    user, sale = await create_sale_with_directory(session, "callback-user", "100")
    await AdvanceService(session).process_pending_sales()
    await ReconciliationService(session).reconcile_sale(sale.id, SaleStatus.APPROVED)
    service = WithdrawalService(session)
    withdrawal = await service.initiate_withdrawal(user.id, Decimal("90"), "callback-withdrawal")
    await service.apply_provider_status(withdrawal.id, "same-event", WithdrawalStatus.CANCELLED, None)
    await service.apply_provider_status(withdrawal.id, "same-event", WithdrawalStatus.CANCELLED, None)
    assert (await service.get_balance(user.id)).available_balance == Decimal("90.00")
    reversals = await session.scalar(
        select(func.count()).select_from(LedgerEntry).where(LedgerEntry.withdrawal_id == withdrawal.id)
    )
    assert reversals == 2
