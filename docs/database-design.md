# Database design

| Table | Role and key constraints |
| --- | --- |
| `users` | Affiliate owner; UUID primary key and unique username. |
| `brands` | Normalized brand catalogue; UUID primary key and unique name. |
| `sales` | A user's affiliate sale. Foreign keys to user/brand, non-negative `NUMERIC(18,2)` earning, and pending-status index. |
| `advance_payouts` | Settled 10% transfer. Unique `sale_id` guarantees at most one advance per sale. |
| `account_balances` | Current per-user withdrawable balance projection plus version; user ID is its primary key. |
| `ledger_entries` | Immutable signed balance movements. Unique `(sale_id, entry_type)` and `(withdrawal_id, entry_type)` prevent duplicate financial effects. |
| `withdrawals` | Provider-facing payout request. Unique `(user_id, idempotency_key)` and unique retry predecessor. |
| `provider_events` | Idempotent audit of provider callbacks; unique external event ID. |

All entities include creation and update audit columns. PostgreSQL uses `NUMERIC(18,2)`, UUID
foreign keys, checks for valid non-negative values, and indexes covering pending-job scans,
per-user withdrawal cooldown queries, and ledger history queries. The Alembic initial revision is
`migrations/versions/0001_initial_schema.py`.
