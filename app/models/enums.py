from enum import StrEnum


class SaleStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AdvanceStatus(StrEnum):
    SETTLED = "settled"


class WithdrawalStatus(StrEnum):
    INITIATED = "initiated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"


class LedgerEntryType(StrEnum):
    FINAL_CREDIT = "final_credit"
    REJECTED_ADJUSTMENT = "rejected_adjustment"
    WITHDRAWAL_DEBIT = "withdrawal_debit"
    WITHDRAWAL_REVERSAL = "withdrawal_reversal"

