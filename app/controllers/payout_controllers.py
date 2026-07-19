from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SaleStatus
from app.schemas.payouts import BrandCreate, ProviderStatusRequest, SaleCreate, UserCreate, WithdrawalCreate
from app.services import AdvanceService, DirectoryService, ReconciliationService, SalesService, WithdrawalService


class PayoutController:
    """Thin HTTP-facing adapter; all rules live in the service layer."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, payload: UserCreate):
        return await DirectoryService(self.session).create_user(payload.username)

    async def create_brand(self, payload: BrandCreate):
        return await DirectoryService(self.session).create_brand(payload.name)

    async def create_sale(self, payload: SaleCreate):
        return await SalesService(self.session).create_sale(
            payload.user_id, payload.brand_id, payload.earning
        )

    async def run_advance_payouts(self):
        return await AdvanceService(self.session).process_pending_sales()

    async def reconcile_sale(self, sale_id: UUID, status: SaleStatus):
        return await ReconciliationService(self.session).reconcile_sale(sale_id, status)

    async def create_withdrawal(self, payload: WithdrawalCreate, idempotency_key: str):
        return await WithdrawalService(self.session).initiate_withdrawal(
            payload.user_id, payload.amount, idempotency_key, payload.retry_of_id
        )

    async def apply_provider_status(self, withdrawal_id: UUID, payload: ProviderStatusRequest):
        return await WithdrawalService(self.session).apply_provider_status(
            withdrawal_id, payload.event_id, payload.status, payload.provider_reference
        )

    async def get_balance(self, user_id: UUID):
        return await WithdrawalService(self.session).get_balance(user_id)
