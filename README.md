# Payout Management API

Production-oriented FastAPI service for affiliate-sale advances, reconciliation, and withdrawals.
It implements the supplied SDE assignment in Python 3.12 with async SQLAlchemy, PostgreSQL,
Alembic, Decimal-only financial calculations, and an immutable balance ledger.

## Quick start with Docker

```bash
# Optionally copy .env.example to .env to override defaults.
# Change INTERNAL_API_KEY before exposing the service.
docker compose up --build
```

The API is available at `http://localhost:8000`; interactive Swagger documentation is at
`http://localhost:8000/docs`. Docker starts PostgreSQL, waits for it to become healthy, runs
Alembic migrations, and then starts the application.

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
# Set DATABASE_URL to a local PostgreSQL database, then:
alembic upgrade head
uvicorn app.main:app --reload
```

Run the scheduled job once on demand with `python -m app.jobs.advance_payout_job`.
The web process also executes it using `ADVANCE_JOB_CRON` (five minutes by default).

## Tests and quality checks

```bash
python -m pytest -q
python -m ruff check app tests migrations
python -m compileall -q app tests migrations
```

Tests use SQLite only as an isolated fast unit-test harness; production and migration workflows
use PostgreSQL. PostgreSQL row locks (`FOR UPDATE` and `SKIP LOCKED`) are exercised by the
production code. To run the real row-lock integration test, set
`POSTGRES_INTEGRATION_URL=postgresql+asyncpg://payout:payout@localhost:5432/payout_test` and run
`python -m pytest -m postgres` after Docker Compose is healthy.
The integration test drops and recreates its target schema, so its URL must point to a disposable
database containing `test` in its name.

## API summary

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/users` | Create a payout user and zero-balance account. |
| `POST /api/v1/brands` | Register a brand. |
| `POST /api/v1/sales` | Create a pending sale. |
| `POST /api/v1/jobs/advance-payouts/run` | Run the idempotent advance job (internal key). |
| `PATCH /api/v1/sales/{id}/reconciliation` | Approve or reject a pending sale (internal key). |
| `GET /api/v1/users/{id}/balance` | Read current withdrawable balance. |
| `POST /api/v1/withdrawals` | Initiate a withdrawal; requires `Idempotency-Key`. |
| `POST /api/v1/withdrawals/{id}/provider-status` | Apply a terminal provider event (internal key). |

Internal operations require `X-Internal-API-Key`. A real deployment should put these endpoints
behind workload authentication and use a secret manager for this value.

See [architecture](docs/architecture.md), [database design](docs/database-design.md),
[API documentation](docs/api.md), [project structure](docs/project-structure.md),
[testing guide](docs/testing.md), [deployment guide](docs/deployment.md),
[implementation plan](docs/implementation-plan.md), and
[assignment verification](docs/assignment-verification.md).
