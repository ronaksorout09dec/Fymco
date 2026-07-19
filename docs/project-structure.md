# Project structure

* `app/api` - versioned FastAPI routes and dependencies.
* `app/controllers` - thin transport adapters.
* `app/services` - domain workflows and transaction orchestration.
* `app/repositories` - persistence queries and locks.
* `app/models` - SQLAlchemy entities and state enums.
* `app/schemas` - Pydantic v2 request and response DTOs.
* `app/core` - configuration, logging, and exceptions.
* `app/db` - async engine, session factory, metadata base.
* `app/middleware` - request correlation and structured request logs.
* `app/jobs` - retry-safe scheduled advance processing.
* `app/utils` - Decimal monetary normalization.
* `migrations` - Alembic revision history.
* `tests` - API, service, and PostgreSQL concurrency coverage.
* `scripts` - local quality-gate runner.
* `docs` - design, setup, API, testing, and verification material.
