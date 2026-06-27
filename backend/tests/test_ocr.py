"""OCR service unit tests."""

import tempfile
from pathlib import Path

import pytest

from app.services.ocr_service import OCRService


@pytest.mark.asyncio
async def test_extract_from_text_file(db_session):
    service = OCRService(db_session)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Employee: John Smith\nHours: 160\nRate: $85\nCompany: Acme\nProject: Alpha\n")
        path = f.name

    try:
        result = await service.extract_from_file(path, "text/plain")
        assert "John Smith" in result["extracted_data"]["employee"]
        assert result["extracted_data"]["hours"] == 160
        assert result["confidence"] > 0
    finally:
        Path(path).unlink(missing_ok=True)
