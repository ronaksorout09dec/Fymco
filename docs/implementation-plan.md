# Implementation plan and requirement traceability

## Scope read from the assignment

The assignment requires a payout-management system for affiliate sales. Every sale starts
as `pending`; a successful, once-only advance of 10% is paid for each eligible pending
sale; an administrator later reconciles a sale to `approved` or `rejected`; an approved
sale pays its earnings less the advance and a rejected sale creates a negative adjustment
equal to its advance. A user may initiate only one withdrawal per 24-hour period. A
cancelled, rejected, or failed withdrawal must restore its amount to the withdrawable
balance and permit a retry. The supplied example (three INR 40 sales with one rejected)
must yield INR 68 final payout after INR 12 in advances.

## Design decisions before implementation

* PostgreSQL is the production datastore. Money uses `NUMERIC(18, 2)` mapped to Python
  `Decimal`; floats are never accepted or calculated.
* A sale's advance is recorded in an `advance_payouts` row with a unique `sale_id`. The
  scheduled job locks candidate sales with `FOR UPDATE SKIP LOCKED`, so overlapping runs
  cannot pay an advance twice.
* Advances are settled transfers, not a second credit to the final withdrawable balance.
  On reconciliation, an approved sale credits only `earning - advance`; a rejected sale
  debits the advance. This directly implements the PDF's payout formula.
* A per-user `account_balances` projection and immutable `ledger_entries` provide fast
  balance reads and an auditable source of every balance change. Balance-changing flows
  lock the projection row in the same transaction as their ledger entry.
* A withdrawal debits withdrawable balance when initiated. A terminal failed, rejected,
  or cancelled withdrawal adds one compensating ledger entry. A unique constraint on the
  reversal entry makes callback retries safe. A failed withdrawal can be retried once for
  the exact restored amount without waiting for the normal cooldown.
* External provider integration is deliberately represented by an authenticated provider
  status callback rather than a fake provider. This keeps the application runnable while
  giving production deployments a reliable, idempotent integration point.

## Requirement-to-implementation checklist

| Assignment requirement | Module / API / table | Service method | Tests |
| --- | --- | --- | --- |
| Sales begin as Pending | `POST /api/v1/sales`; `sales` | `SalesService.create_sale` | `test_create_sale_starts_pending` |
| Pending sale advance is 10% of earnings | `advance_payouts`; background `advance_payout_job` | `AdvanceService.process_pending_sales` | `test_advance_is_exactly_ten_percent` |
| A paid advance is never repeated | unique `advance_payouts.sale_id`; job lock | `AdvanceService.process_pending_sales` | `test_advance_job_is_rerunnable` and concurrency test |
| Admin reconciles to approved or rejected | `PATCH /api/v1/sales/{id}/reconciliation`; `sales` | `ReconciliationService.reconcile_sale` | `test_reconciliation_accepts_terminal_statuses_only` |
| Approved final payout is earning minus advance | `ledger_entries` (`final_credit`) | `ReconciliationService.reconcile_sale` | `test_approved_sale_credits_remaining_earnings` |
| Rejected sale adjustment is negative advance | `ledger_entries` (`rejected_adjustment`) | `ReconciliationService.reconcile_sale` | `test_rejected_sale_debits_advance` |
| Reference example produces INR 68 final payout | aggregate balance / ledger | reconciliation and `BalancesService` | `test_reference_example_final_total_is_68` |
| One withdrawal per 24 hours | `withdrawals`, index by user and created time | `WithdrawalService.initiate_withdrawal` | `test_withdrawal_cooldown` |
| Failed / rejected / cancelled payout restores amount | `withdrawals`, `ledger_entries` (`withdrawal_reversal`) | `WithdrawalService.apply_provider_status` | parameterized recovery test |
| Recovery permits another withdrawal | `POST /api/v1/withdrawals` with `retry_of` | `WithdrawalService.initiate_withdrawal` | `test_recovered_withdrawal_can_be_retried` |
| LLD | `docs/architecture.md` | n/a | reviewed with project checklist |
| Database schemas, relationships, indexes | SQLAlchemy models + Alembic revision + `docs/database-design.md` | repositories | migration/schema tests |
| Class design / equivalent | `app/services`, `app/repositories`, schemas and domain enums | dependency-injected services | unit tests |
| APIs / endpoints | `app/api/v1` and OpenAPI | controllers delegate only | API tests |
| Edge cases and failure handling | exceptions, global handlers, transactions, callback rules | all financial services | failure/concurrency/idempotency tests |
| Working JavaScript or Python implementation | Python 3.12 FastAPI app | all modules | pytest suite |
| README and documentation | `README.md`, `docs/` | n/a | installation command verification |

## Implementation sequence

1. Scaffold configuration, database/session lifecycle, exception handling, logging, and
   clean-architecture folders.
2. Add normalized models, repositories, Alembic schema, and dependency injection.
3. Implement sales, advance job, reconciliation, account ledger, and withdrawal services
   using short ACID transactions and row-level locking.
4. Expose versioned REST controllers with Pydantic v2 validation, idempotency headers,
   documented response shapes, and an authenticated provider callback.
5. Add Docker, Docker Compose, health checks, scheduled-job command, and operational docs.
6. Run static compilation and the complete pytest suite. Record final traceability in
   `docs/assignment-verification.md` only after tests pass.
