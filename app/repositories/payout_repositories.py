from uuid import UUID

from sqlalchemy import select
from app.models.entities import AccountBalance, AdvancePayout, LedgerEntry, ProviderEvent, Sale, Withdrawal
from app.models.enums import SaleStatus
from app.repositories.base import BaseRepository


class SaleRepository(BaseRepository):
    @staticmethod
    def pending_without_advance_statement():
        return (
            select(Sale)
            .outerjoin(AdvancePayout, AdvancePayout.sale_id == Sale.id)
            .where(Sale.status == SaleStatus.PENDING, AdvancePayout.id.is_(None))
            .order_by(Sale.created_at)
            .with_for_update(of=Sale, skip_locked=True)
        )

    async def pending_without_advance_for_update(self) -> list[Sale]:
        statement = self.pending_without_advance_statement()
        return list((await self.session.scalars(statement)).all())


class BalanceRepository(BaseRepository):
    async def get_locked_for_user(self, user_id: UUID) -> AccountBalance:
        balance = await self.session.scalar(
            select(AccountBalance)
            .where(AccountBalance.user_id == user_id)
            .with_for_update()
        )
        if balance is None:
            raise RuntimeError(f"Missing balance projection for user {user_id}")
        return balance

    async def add_entry(self, entry: LedgerEntry, balance: AccountBalance) -> None:
        balance.available_balance += entry.amount
        balance.version += 1
        self.session.add(entry)


class WithdrawalRepository(BaseRepository):
    async def by_idempotency_key(self, user_id: UUID, key: str) -> Withdrawal | None:
        return await self.session.scalar(
            select(Withdrawal).where(
                Withdrawal.user_id == user_id, Withdrawal.idempotency_key == key
            )
        )

    async def latest_for_user(self, user_id: UUID) -> Withdrawal | None:
        return await self.session.scalar(
            select(Withdrawal)
            .where(Withdrawal.user_id == user_id)
            .order_by(Withdrawal.created_at.desc())
            .limit(1)
        )

    async def get_locked(self, withdrawal_id: UUID) -> Withdrawal:
        withdrawal = await self.session.scalar(
            select(Withdrawal).where(Withdrawal.id == withdrawal_id).with_for_update()
        )
        if withdrawal is None:
            from app.core.exceptions import NotFoundError

            raise NotFoundError(f"Withdrawal {withdrawal_id} was not found")
        return withdrawal

    async def provider_event(self, event_id: str) -> ProviderEvent | None:
        return await self.session.scalar(
            select(ProviderEvent).where(ProviderEvent.event_id == event_id)
        )
