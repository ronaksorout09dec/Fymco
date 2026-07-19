# Docker and deployment guide

1. Create a managed PostgreSQL 16+ database and set `DATABASE_URL` to its asyncpg URL.
2. Store `INTERNAL_API_KEY` in the platform secret manager; never use the development fallback.
3. Build the supplied Dockerfile. Its startup command applies `alembic upgrade head` before
   starting Uvicorn.
4. Configure the platform health probe to `GET /health` and route traffic to port 8000.
5. Run a separate scheduler/worker deployment in a horizontally scaled production environment,
   or ensure only one web replica has `ADVANCE_JOB_ENABLED=true`. The job is idempotent, but a
   separate worker avoids duplicate scheduler ownership.
6. Configure structured log collection and alert on HTTP 5xx, failed migrations, and repeated
   provider callback errors.

For local containers, `docker compose up --build` starts both the PostgreSQL and API services.
`docker compose config --quiet` validates the compose manifest without a running daemon.
