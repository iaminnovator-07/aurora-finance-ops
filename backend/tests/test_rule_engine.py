"""Rule engine unit tests."""

import pytest
from decimal import Decimal

from app.models.invoice import Invoice
from app.services.rule_engine_service import RuleEngineService


@pytest.mark.asyncio
async def test_validate_data_missing_fields(db_session):
    service = RuleEngineService(db_session)
    result = await service.validate_data({"subject": "Invoice"})
    assert result["failed_count"] >= 1
    assert any(not r["passed"] for r in result["results"])


@pytest.mark.asyncio
async def test_validate_invoice_budget(db_session):
    from app.models.client import Client

    client = Client(name="Test Co", domain="test.com", budget_limit=Decimal("1000"))
    db_session.add(client)
    await db_session.flush()

    invoice = Invoice(
        invoice_number="INV-TEST-001",
        client_id=client.id,
        vendor_name="Test Co",
        total_amount=Decimal("50000"),
        currency="USD",
        status="draft",
    )
    db_session.add(invoice)
    await db_session.flush()

    service = RuleEngineService(db_session)
    result = await service.validate_invoice(invoice.id)
    assert result["total_rules"] >= 5
    budget_fail = [r for r in result["results"] if "budget" in r["rule_name"].lower()]
    assert budget_fail
    assert not budget_fail[0]["passed"]
