# Final assignment verification

Verification was performed after implementation with `python -m pytest -q` (10 passed; one
PostgreSQL-only concurrency test skipped without a disposable test database URL),
`python -m ruff check app tests migrations`, and `python -m compileall -q app tests migrations`.
Docker Compose was built and started successfully; both containers became healthy. A live API
smoke flow verified the ₹100 -> ₹10 advance -> ₹90 approved balance sequence and restoration of
the ₹90 balance after a failed withdrawal.

| Requirement | Implementation location | Status |
| --- | --- | --- |
| Pending sale state | `SalesService.create_sale`; `sales.status` | Complete |
| 10% advance for every eligible pending sale | `AdvanceService.process_pending_sales`; `advance_payouts` | Complete |
| No duplicate advances across reruns | row lock, unique `sale_id`, `test_advance_is_exactly_ten_percent_and_rerunnable` | Complete |
| Admin approves or rejects sales | reconciliation controller and service | Complete |
| Approved final payout: earnings minus advance | `ReconciliationService.reconcile_sale` final-credit entry | Complete |
| Rejected final adjustment: negative advance | reconciliation rejected-adjustment entry | Complete |
| PDF three-sale example ends at INR 68 | `test_reference_example_final_total_is_68` | Complete |
| One payout withdrawal per 24 hours | `WithdrawalService.initiate_withdrawal` | Complete |
| Failed/cancelled/rejected payout restores funds | provider callback and withdrawal-reversal ledger entry | Complete |
| Recovery allows retry | exact-amount `retry_of_id` path and service test | Complete |
| LLD, schemas, relationships, APIs, design trade-offs | `docs/architecture.md`, `docs/database-design.md`, Swagger | Complete |
| Working Python implementation | FastAPI app, async SQLAlchemy, Alembic, Docker | Complete |
| Edge cases, failure safety, concurrency, idempotency | centralized errors, ACID transactions, locks, constraints, unit tests plus `tests/test_postgres_concurrency.py` | Complete |
| README and repository documentation | `README.md`, `docs/` | Complete |
