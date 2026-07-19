from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_session
from app.main import app
from app.services import AdvanceService, DirectoryService, ReconciliationService, SalesService
from app.models.enums import SaleStatus


@pytest.mark.asyncio
async def test_api_returns_validation_and_authorization_errors(session_factory):
    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        invalid = await client.post("/api/v1/users", json={"username": ""})
        denied = await client.post("/api/v1/jobs/advance-payouts/run")
    app.dependency_overrides.clear()
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"
    assert denied.status_code == 401


@pytest.mark.asyncio
async def test_api_withdrawal_requires_idempotency_key_and_recovers_failed_payout(session_factory):
    async with session_factory() as seed_session:
        directory = DirectoryService(seed_session)
        user = await directory.create_user("api-user")
        brand = await directory.create_brand("api-brand")
        sale = await SalesService(seed_session).create_sale(user.id, brand.id, Decimal("100"))
        await AdvanceService(seed_session).process_pending_sales()
        await ReconciliationService(seed_session).reconcile_sale(sale.id, SaleStatus.APPROVED)

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    transport = ASGITransport(app=app)
    payload = {"user_id": str(user.id), "amount": "90.00"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing_key = await client.post("/api/v1/withdrawals", json=payload)
        created = await client.post("/api/v1/withdrawals", json=payload, headers={"Idempotency-Key": "api-key"})
        withdrawal_id = created.json()["id"]
        recovered = await client.post(
            f"/api/v1/withdrawals/{withdrawal_id}/provider-status",
            json={"event_id": "api-provider-event", "status": "failed"},
            headers={"X-Internal-API-Key": "development-only-key"},
        )
        balance = await client.get(f"/api/v1/users/{user.id}/balance")
    app.dependency_overrides.clear()
    assert missing_key.status_code == 422
    assert created.status_code == 201
    assert recovered.status_code == 200
    assert balance.json()["available_balance"] == "90.00"
