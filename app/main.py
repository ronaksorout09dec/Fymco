import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import router as v1_router
from app.core.exceptions import ApplicationError
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.jobs.scheduler import start_scheduler
from app.middleware.request_logging import RequestLoggingMiddleware

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = start_scheduler()
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Payout Management API", version="1.0.0", lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.include_router(v1_router)


@app.exception_handler(ApplicationError)
async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": error.error_code, "message": error.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Invalid request", "details": error.errors()}},
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, error: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", exc_info=error)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred"}},
    )


@app.get("/health", tags=["operations"])
async def health_check() -> dict[str, str]:
    async with SessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}
