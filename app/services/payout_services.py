import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.entities import AccountBalance, AdvancePayout, Brand, LedgerEntry, ProviderEvent, Sale, User, Withdrawal
from app.models.enums import AdvanceStatus, LedgerEntryType, SaleStatus, WithdrawalStatus
from app.repositories import BalanceRepository, SaleRepository, WithdrawalRepository
from app.services.transactions import transactional
from app.utils.money import money

logger = logging.getLogger(__name__)
ADVANCE_RATE = Decimal("0.10")
WITHDRAWAL_COOLDOWN = timedelta(hours=24)
FAILED_WITHDRAWAL_STATUSES = {
    WithdrawalStatus.CANCELLED,
    WithdrawalStatus.REJECTED,
    WithdrawalStatus.FAILED,
}

class DirectoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, username: str) -> User:
        async with transactional(self.session):
            existing = await self.session.scalar(select(User).where(User.username == username))
            if existing:
                raise ConflictError("A user with this username already exists")
            user = User(username=username)
            self.session.add(user)
            await self.session.flush()
            self.session.add(AccountBalance(user_id=user.id, available_balance=Decimal("0.00")))
        return user

    async def create_brand(self, name: str) -> Brand:
        async with transactional(self.session):
            existing = await self.session.scalar(select(Brand).where(Brand.name == name))
            if existing:
                raise ConflictError("A brand with this name already exists")
            brand = Brand(name=name)
            self.session.add(brand)
        return brand


class SalesService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_sale(self, user_id: UUID, brand_id: UUID, earning: Decimal) -> Sale:
        async with transactional(self.session):
            if await self.session.get(User, user_id) is None:
                raise NotFoundError(f"User {user_id} was not found")
            if await self.session.get(Brand, brand_id) is None:
                raise NotFoundError(f"Brand {brand_id} was not found")
            sale = Sale(user_id=user_id, brand_id=brand_id, earning=money(earning))
            self.session.add(sale)
        return sale


class AdvanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def process_pending_sales(self) -> list[AdvancePayout]:
        """Settle missing advances once. Safe for scheduled/manual concurrent runs."""
        async with transactional(self.session):
            candidates = await SaleRepository(self.session).pending_without_advance_for_update()
            payouts: list[AdvancePayout] = []
            for sale in candidates:
                payout = AdvancePayout(
                    sale_id=sale.id,
                    user_id=sale.user_id,
                    amount=money(sale.earning * ADVANCE_RATE),
                    status=AdvanceStatus.SETTLED,
                )
                self.session.add(payout)
                payouts.append(payout)
            await self.session.flush()
            logger.info("advance_payouts_settled", extra={"count": len(payouts)})
        return payouts


class ReconciliationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def reconcile_sale(self, sale_id: UUID, final_status: SaleStatus) -> Sale:
        if final_status not in {SaleStatus.APPROVED, SaleStatus.REJECTED}:
            raise BusinessRuleError("A sale can only be reconciled as approved or rejected")
        async with transactional(self.session):
            sale = await SaleRepository(self.session).get_locked_or_raise(Sale, sale_id)
            if sale.status != SaleStatus.PENDING:
                raise ConflictError("A sale can only be reconciled once")
            advance = await self.session.scalar(
                select(AdvancePayout).where(AdvancePayout.sale_id == sale.id).with_for_update()
            )
            advance_amount = advance.amount if advance else Decimal("0.00")
            entry_type = (
                LedgerEntryType.FINAL_CREDIT
                if final_status == SaleStatus.APPROVED
                else LedgerEntryType.REJECTED_ADJUSTMENT
            )
            amount = money(sale.earning - advance_amount) if final_status == SaleStatus.APPROVED else -advance_amount
            balance = await BalanceRepository(self.session).get_locked_for_user(sale.user_id)
            entry = LedgerEntry(
                user_id=sale.user_id,
                sale_id=sale.id,
                entry_type=entry_type,
                amount=amount,
                description=f"{final_status.value.title()} reconciliation for sale {sale.id}",
            )
            await BalanceRepository(self.session).add_entry(entry, balance)
            sale.status = final_status
            sale.reconciled_at = datetime.now(UTC)
            logger.info("sale_reconciled", extra={"sale_id": str(sale.id), "status": final_status.value, "amount": str(amount)})
        return sale


class WithdrawalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WithdrawalRepository(session)

    async def initiate_withdrawal(
        self, user_id: UUID, amount: Decimal, idempotency_key: str, retry_of_id: UUID | None = None
    ) -> Withdrawal:
        async with transactional(self.session):
            existing = await self.repository.by_idempotency_key(user_id, idempotency_key)
            if existing:
                return existing
            if await self.session.get(User, user_id) is None:
                raise NotFoundError(f"User {user_id} was not found")
            balance = await BalanceRepository(self.session).get_locked_for_user(user_id)
            # Recheck after serializing on the account row: a concurrent request may
            # have committed while this request was waiting for the lock.
            existing = await self.repository.by_idempotency_key(user_id, idempotency_key)
            if existing:
                return existing
            is_valid_retry = False
            if retry_of_id:
                previous = await self.repository.get_locked(retry_of_id)
                if previous.user_id != user_id or previous.status not in FAILED_WITHDRAWAL_STATUSES:
                    raise BusinessRuleError("retry_of_id must reference this user's recovered withdrawal")
                if previous.failure_reversed_at is None or money(previous.amount) != money(amount):
                    raise BusinessRuleError("A retry must use the exact recovered amount")
                is_valid_retry = True
            latest = await self.repository.latest_for_user(user_id)
            now = datetime.now(UTC)
            latest_created_at = latest.created_at if latest else None
            if latest_created_at and latest_created_at.tzinfo is None:
                latest_created_at = latest_created_at.replace(tzinfo=UTC)
            if latest_created_at and latest_created_at + WITHDRAWAL_COOLDOWN > now and not is_valid_retry:
                raise BusinessRuleError("Only one withdrawal may be initiated in a 24-hour period")
            requested_amount = money(amount)
            if balance.available_balance < requested_amount:
                raise BusinessRuleError("Insufficient withdrawable balance")
            withdrawal = Withdrawal(
                user_id=user_id,
                amount=requested_amount,
                idempotency_key=idempotency_key,
                retry_of_id=retry_of_id,
            )
            self.session.add(withdrawal)
            await self.session.flush()
            await BalanceRepository(self.session).add_entry(
                LedgerEntry(
                    user_id=user_id,
                    withdrawal_id=withdrawal.id,
                    entry_type=LedgerEntryType.WITHDRAWAL_DEBIT,
                    amount=-requested_amount,
                    description=f"Withdrawal {withdrawal.id} initiated",
                ),
                balance,
            )
            logger.info("withdrawal_initiated", extra={"withdrawal_id": str(withdrawal.id), "amount": str(requested_amount)})
        return withdrawal

    async def apply_provider_status(
        self, withdrawal_id: UUID, event_id: str, status: WithdrawalStatus, provider_reference: str | None
    ) -> Withdrawal:
        if status == WithdrawalStatus.INITIATED:
            raise BusinessRuleError("A provider callback must contain a terminal status")
        async with transactional(self.session):
            seen = await self.repository.provider_event(event_id)
            if seen:
                return await self.repository.get_locked(seen.withdrawal_id)
            withdrawal = await self.repository.get_locked(withdrawal_id)
            # A competing callback might have inserted the event while this request
            # waited on the withdrawal lock.
            seen = await self.repository.provider_event(event_id)
            if seen:
                return withdrawal
            if withdrawal.status != WithdrawalStatus.INITIATED:
                if withdrawal.status == status:
                    self.session.add(ProviderEvent(event_id=event_id, withdrawal_id=withdrawal.id, status=status))
                    return withdrawal
                raise ConflictError("Withdrawal already has a different terminal status")
            withdrawal.status = status
            if provider_reference:
                withdrawal.provider_reference = provider_reference
            self.session.add(ProviderEvent(event_id=event_id, withdrawal_id=withdrawal.id, status=status))
            if status in FAILED_WITHDRAWAL_STATUSES:
                balance = await BalanceRepository(self.session).get_locked_for_user(withdrawal.user_id)
                await BalanceRepository(self.session).add_entry(
                    LedgerEntry(
                        user_id=withdrawal.user_id,
                        withdrawal_id=withdrawal.id,
                        entry_type=LedgerEntryType.WITHDRAWAL_REVERSAL,
                        amount=withdrawal.amount,
                        description=f"Withdrawal {withdrawal.id} {status.value}; funds restored",
                    ),
                    balance,
                )
                withdrawal.failure_reversed_at = datetime.now(UTC)
            logger.info("withdrawal_provider_status", extra={"withdrawal_id": str(withdrawal.id), "status": status.value})
        return withdrawal

    async def get_balance(self, user_id: UUID) -> AccountBalance:
        async with transactional(self.session):
            balance = await self.session.get(AccountBalance, user_id)
            if balance is None:
                raise NotFoundError(f"Balance for user {user_id} was not found")
        return balance
