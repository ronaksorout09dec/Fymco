from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.api.dependencies import DatabaseSession, require_internal_key
from app.controllers.payout_controllers import PayoutController
from app.schemas.common import BalanceResponse
from app.schemas.payouts import (
    AdvanceRunResponse,
    BrandCreate,
    BrandResponse,
    ProviderStatusRequest,
    SaleCreate,
    SaleResponse,
    ReconciliationRequest,
    UserCreate,
    UserResponse,
    WithdrawalCreate,
    WithdrawalResponse,
)

router = APIRouter(prefix="/api/v1", tags=["payouts"])


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: DatabaseSession):
    return await PayoutController(session).create_user(payload)


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(payload: BrandCreate, session: DatabaseSession):
    return await PayoutController(session).create_brand(payload)


@router.post("/sales", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
async def create_sale(payload: SaleCreate, session: DatabaseSession):
    return await PayoutController(session).create_sale(payload)


@router.post("/jobs/advance-payouts/run", response_model=AdvanceRunResponse, dependencies=[Depends(require_internal_key)])
async def run_advance_payouts(session: DatabaseSession):
    payouts = await PayoutController(session).run_advance_payouts()
    return {"processed": payouts}


@router.patch("/sales/{sale_id}/reconciliation", response_model=SaleResponse, dependencies=[Depends(require_internal_key)])
async def reconcile_sale(sale_id: UUID, payload: ReconciliationRequest, session: DatabaseSession):
    return await PayoutController(session).reconcile_sale(sale_id, payload.status)


@router.get("/users/{user_id}/balance", response_model=BalanceResponse)
async def get_balance(user_id: UUID, session: DatabaseSession):
    return await PayoutController(session).get_balance(user_id)


@router.post("/withdrawals", response_model=WithdrawalResponse, status_code=status.HTTP_201_CREATED)
async def create_withdrawal(
    payload: WithdrawalCreate,
    session: DatabaseSession,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)],
):
    return await PayoutController(session).create_withdrawal(payload, idempotency_key)


@router.post("/withdrawals/{withdrawal_id}/provider-status", response_model=WithdrawalResponse, dependencies=[Depends(require_internal_key)])
async def provider_status(withdrawal_id: UUID, payload: ProviderStatusRequest, session: DatabaseSession):
    return await PayoutController(session).apply_provider_status(withdrawal_id, payload)
