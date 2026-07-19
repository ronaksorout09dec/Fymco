"""Initial normalized payout schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-17
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None

sale_status = sa.Enum("PENDING", "APPROVED", "REJECTED", name="salestatus")
advance_status = sa.Enum("SETTLED", name="advancestatus")
withdrawal_status = sa.Enum("INITIATED", "COMPLETED", "CANCELLED", "REJECTED", "FAILED", name="withdrawalstatus")
ledger_type = sa.Enum("FINAL_CREDIT", "REJECTED_ADJUSTMENT", "WITHDRAWAL_DEBIT", "WITHDRAWAL_REVERSAL", name="ledgerentrytype")


def audit_columns():
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("username", sa.String(100), nullable=False, unique=True), *audit_columns())
    op.create_table("brands", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("name", sa.String(100), nullable=False, unique=True), *audit_columns())
    op.create_table("sales", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("brand_id", sa.Uuid(), sa.ForeignKey("brands.id"), nullable=False), sa.Column("status", sale_status, nullable=False), sa.Column("earning", sa.Numeric(18, 2), nullable=False), sa.Column("reconciled_at", sa.DateTime(timezone=True)), *audit_columns(), sa.CheckConstraint("earning >= 0", name="ck_sales_non_negative_earning"))
    op.create_index("ix_sales_user_id", "sales", ["user_id"])
    op.create_index("ix_sales_brand_id", "sales", ["brand_id"])
    op.create_index("ix_sales_pending_created", "sales", ["status", "created_at"])
    op.create_table("account_balances", sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True), sa.Column("available_balance", sa.Numeric(18, 2), nullable=False), sa.Column("version", sa.Integer(), nullable=False), *audit_columns())
    op.create_table("advance_payouts", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("sale_id", sa.Uuid(), sa.ForeignKey("sales.id"), nullable=False, unique=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False), sa.Column("status", advance_status, nullable=False), sa.Column("settled_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False), *audit_columns(), sa.CheckConstraint("amount >= 0", name="ck_advance_non_negative_amount"))
    op.create_index("ix_advance_payouts_user_id", "advance_payouts", ["user_id"])
    op.create_table("withdrawals", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False), sa.Column("status", withdrawal_status, nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("provider_reference", sa.String(128), unique=True), sa.Column("retry_of_id", sa.Uuid(), sa.ForeignKey("withdrawals.id"), unique=True), sa.Column("failure_reversed_at", sa.DateTime(timezone=True)), *audit_columns(), sa.CheckConstraint("amount > 0", name="ck_withdrawal_positive_amount"), sa.UniqueConstraint("user_id", "idempotency_key", name="uq_withdrawal_user_idempotency"))
    op.create_index("ix_withdrawal_user_created", "withdrawals", ["user_id", "created_at"])
    op.create_table("ledger_entries", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False), sa.Column("entry_type", ledger_type, nullable=False), sa.Column("amount", sa.Numeric(18, 2), nullable=False), sa.Column("sale_id", sa.Uuid(), sa.ForeignKey("sales.id")), sa.Column("withdrawal_id", sa.Uuid(), sa.ForeignKey("withdrawals.id")), sa.Column("description", sa.String(255), nullable=False), *audit_columns(), sa.UniqueConstraint("sale_id", "entry_type", name="uq_ledger_sale_entry_type"), sa.UniqueConstraint("withdrawal_id", "entry_type", name="uq_ledger_withdrawal_entry_type"))
    op.create_index("ix_ledger_user_created", "ledger_entries", ["user_id", "created_at"])
    op.create_table("provider_events", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("event_id", sa.String(128), nullable=False, unique=True), sa.Column("withdrawal_id", sa.Uuid(), sa.ForeignKey("withdrawals.id"), nullable=False), sa.Column("status", withdrawal_status, nullable=False), *audit_columns())
    op.create_index("ix_provider_events_withdrawal_id", "provider_events", ["withdrawal_id"])


def downgrade() -> None:
    for table in ["provider_events", "ledger_entries", "withdrawals", "advance_payouts", "account_balances", "sales", "brands", "users"]:
        op.drop_table(table)
