# Testing guide

Run `python scripts/run_quality_checks.py` after installing `requirements-dev.txt`. It compiles
the project, executes the fast suite, and lints source code. The suite covers the pending-sale
default, exact 10% rounding, rerunnable advance job, reconciliation state machine, the PDF's
INR 68 example, withdrawal cooldown, idempotency, callback idempotency, recovery, validation,
and internal authorization.

The default suite uses isolated SQLite files for speed. The separately marked `postgres` test
requires a disposable PostgreSQL URL containing `test`, because it drops and recreates its schema:

```bash
POSTGRES_INTEGRATION_URL=postgresql+asyncpg://payout:payout@localhost:5432/payout_test python -m pytest -m postgres
```

This test runs concurrent identical withdrawal requests and verifies that PostgreSQL locking plus
idempotency creates only one withdrawal.
