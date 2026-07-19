from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from app.models.enums import SaleStatus, WithdrawalStatus
from app.schemas.common import ORMModel

Money = Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class UserCreate(BaseModel):
    username: Name


class UserResponse(ORMModel):
    id: UUID
    username: str
    created_at: datetime


class BrandCreate(BaseModel):
    name: Name


class BrandResponse(ORMModel):
    id: UUID
    name: str


class SaleCreate(BaseModel):
    user_id: UUID
    brand_id: UUID
    earning: Money


class SaleResponse(ORMModel):
    id: UUID
    user_id: UUID
    brand_id: UUID
    status: SaleStatus
    earning: Decimal
    reconciled_at: datetime | None
    created_at: datetime


class ReconciliationRequest(BaseModel):
    status: SaleStatus


class AdvancePayoutResponse(ORMModel):
    id: UUID
    sale_id: UUID
    user_id: UUID
    amount: Decimal
    settled_at: datetime


class AdvanceRunResponse(BaseModel):
    processed: list[AdvancePayoutResponse]


class WithdrawalCreate(BaseModel):
    user_id: UUID
    amount: Money
    retry_of_id: UUID | None = None


class WithdrawalResponse(ORMModel):
    id: UUID
    user_id: UUID
    amount: Decimal
    status: WithdrawalStatus
    provider_reference: str | None
    retry_of_id: UUID | None
    failure_reversed_at: datetime | None
    created_at: datetime


class ProviderStatusRequest(BaseModel):
    event_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
    status: WithdrawalStatus
    provider_reference: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)] | None = None
