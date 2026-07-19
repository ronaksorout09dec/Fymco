from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BalanceResponse(ORMModel):
    user_id: UUID
    available_balance: Decimal
    version: int


class MessageResponse(BaseModel):
    message: str
