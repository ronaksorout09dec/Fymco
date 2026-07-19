import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.base import Base
from app.models.enums import AdvanceStatus, LedgerEntryType, SaleStatus, WithdrawalStatus


class AuditMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(AuditMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sales: Mapped[list["Sale"]] = relationship(back_populates="user")
    balance: Mapped["AccountBalance"] = relationship(back_populates="user", uselist=False)


class Brand(AuditMixin, Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sales: Mapped[list["Sale"]] = relationship(back_populates="brand")


class Sale(AuditMixin, Base):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("earning >= 0", name="ck_sales_non_negative_earning"),
        Index("ix_sales_pending_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id"), nullable=False, index=True)
    status: Mapped[SaleStatus] = mapped_column(Enum(SaleStatus), default=SaleStatus.PENDING, nullable=False)
    earning: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    reconciled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="sales")
    brand: Mapped[Brand] = relationship(back_populates="sales")
    advance_payout: Mapped["AdvancePayout | None"] = relationship(back_populates="sale", uselist=False)


class AccountBalance(AuditMixin, Base):
    __tablename__ = "account_balances"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    user: Mapped[User] = relationship(back_populates="balance")


class AdvancePayout(AuditMixin, Base):
    __tablename__ = "advance_payouts"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_advance_non_negative_amount"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sale_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sales.id"), unique=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[AdvanceStatus] = mapped_column(Enum(AdvanceStatus), default=AdvanceStatus.SETTLED, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sale: Mapped[Sale] = relationship(back_populates="advance_payout")


class Withdrawal(AuditMixin, Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_withdrawal_positive_amount"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_withdrawal_user_idempotency"),
        UniqueConstraint("retry_of_id", name="uq_withdrawal_retry_of"),
        Index("ix_withdrawal_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[WithdrawalStatus] = mapped_column(Enum(WithdrawalStatus), default=WithdrawalStatus.INITIATED, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(128), unique=True)
    retry_of_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("withdrawals.id"))
    failure_reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LedgerEntry(AuditMixin, Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("sale_id", "entry_type", name="uq_ledger_sale_entry_type"),
        UniqueConstraint("withdrawal_id", "entry_type", name="uq_ledger_withdrawal_entry_type"),
        Index("ix_ledger_user_created", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    entry_type: Mapped[LedgerEntryType] = mapped_column(Enum(LedgerEntryType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    sale_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sales.id"))
    withdrawal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("withdrawals.id"))
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class ProviderEvent(AuditMixin, Base):
    __tablename__ = "provider_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    withdrawal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("withdrawals.id"), nullable=False, index=True)
    status: Mapped[WithdrawalStatus] = mapped_column(Enum(WithdrawalStatus), nullable=False)
