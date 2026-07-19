# Architecture and design decisions

## Layers

`app/api` contains versioned FastAPI routes only. Routes call `PayoutController`; controllers
translate DTOs to service calls but hold no business rules. `app/services` owns financial rules
and transaction boundaries. `app/repositories` encapsulates query and row-lock operations.
`app/models` defines persistence entities, and `app/schemas` defines Pydantic v2 HTTP contracts.

## Financial flow

1. Sales are created only as `pending`.
2. The advance job locks pending sales without an `advance_payouts` row using PostgreSQL
   `FOR UPDATE SKIP LOCKED`, creates one settled advance of `earning * 0.10`, and commits.
3. Reconciliation locks the pending sale. Approval credits `earning - advance`; rejection
   debits the advance. The sale cannot be reconciled a second time.
4. Every final balance change appends an immutable ledger entry and updates a locked balance
   projection in one ACID transaction.
5. A withdrawal locks the balance, validates the cooldown and funds, records a debit entry,
   and creates an `initiated` withdrawal. A terminal failed/cancelled/rejected provider callback
   creates exactly one compensating credit. The unique ledger key and provider event ID make
   callback retries idempotent.

## Concurrency and idempotency

* One advance per sale is protected by a unique `advance_payouts.sale_id` constraint plus a
  skip-locked selection strategy.
* One reconciliation is protected by a sale row lock and state-transition check.
* A balance row is locked before any debit or credit; concurrent withdrawals therefore serialize.
* `Idempotency-Key` is unique per user and withdrawal; replays return the original withdrawal.
* Provider event IDs are globally unique, and reversal ledger entries are unique per withdrawal.
* The advance job is safe to run repeatedly; the scheduler merely invokes that idempotent command.

## Failure model and trade-offs

The service intentionally does not pretend to transfer money to an external provider. Instead,
it exposes a secure provider-status callback that a real payment adapter/webhook calls after a
transfer. This preserves accurate accounting and retry semantics without embedding fake payment
network behavior. A production provider adapter should authenticate signed webhooks and place an
outbox/event relay between database commits and external side effects.

Rejected sale adjustments may make the available balance negative if an advance was already paid.
That debt is deliberately retained so it offsets later approved earnings; new withdrawals require
a positive sufficient balance.
