"""Trust engine unit tests."""

import pytest
from types import SimpleNamespace

from app.services.trust_engine_service import TrustEngineService


@pytest.mark.asyncio
async def test_trust_adhoc_scoring(db_session):
    service = TrustEngineService(db_session)
    result = await service.check_adhoc(
        from_email="billing@acme-logistics.com",
        subject="Invoice INV-2381 for October",
        body="Please find attached invoice for services rendered.",
    )
    assert "overall_score" in result
    assert 0 <= result["overall_score"] <= 100
    assert result["identity_score"] >= 0
    assert len(result["reasoning_timeline"]) >= 3


@pytest.mark.asyncio
async def test_spam_detection_low_trust(db_session):
    service = TrustEngineService(db_session)
    result = await service.check_adhoc(
        from_email="finance@unknown-vendor.biz",
        subject="URGENT: Wire transfer required",
        body="Click here immediately to wire funds.",
    )
    assert result["overall_score"] < 80
    assert result["risk_level"] in ("medium", "high", "critical")
