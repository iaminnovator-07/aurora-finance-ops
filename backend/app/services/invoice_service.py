"""Invoice creation and management service."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ProcessingError
from app.models.base import InvoiceStatus
from app.models.invoice import Invoice
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.misc_repository import DocumentExtractionRepository


class InvoiceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.invoice_repo = InvoiceRepository(session)
        self.extraction_repo = DocumentExtractionRepository(session)

    async def create_from_extraction(
        self,
        extraction_id: UUID,
        email_id: UUID | None = None,
        client_id: UUID | None = None,
        trust_score: float | None = None,
    ) -> Invoice:
        extraction = await self.extraction_repo.get_by_id(extraction_id)
        if not extraction:
            raise NotFoundError("DocumentExtraction", str(extraction_id))

        normalized = extraction.normalized_data or extraction.extracted_data or {}
        invoice_number = await self.generate_invoice_number()

        subtotal = self._decimal(normalized.get("subtotal") or normalized.get("total"))
        hours = normalized.get("hours")
        rate = normalized.get("rate")
        if not subtotal and hours and rate:
            subtotal = Decimal(str(hours)) * Decimal(str(rate))

        tax_rate = Decimal("0.0")
        tax_amount = self._decimal(normalized.get("tax"))
        if subtotal and tax_amount:
            tax_rate = (tax_amount / subtotal).quantize(Decimal("0.0001"))
        elif subtotal:
            tax_amount = Decimal("0.00")

        total = self._decimal(normalized.get("total")) or subtotal
        if total and tax_amount and subtotal and total == subtotal:
            total = subtotal + tax_amount

        line_items = self._build_line_items(normalized, subtotal)

        invoice = Invoice(
            invoice_number=invoice_number,
            email_id=email_id,
            client_id=client_id,
            extraction_id=extraction_id,
            status=InvoiceStatus.DRAFT.value,
            vendor_name=normalized.get("company") or normalized.get("vendor"),
            issue_date=self._parse_date(normalized.get("date")),
            currency=normalized.get("currency", "USD"),
            subtotal=subtotal,
            tax_amount=tax_amount,
            tax_rate=tax_rate,
            total_amount=total,
            trust_score=trust_score,
            confidence_score=float(extraction.confidence or normalized.get("confidence", 0)),
            line_items=line_items,
            extracted_fields={
                "employee": normalized.get("employee"),
                "hours": normalized.get("hours"),
                "rate": normalized.get("rate"),
                "project": normalized.get("project"),
                "ot_hours": normalized.get("ot_hours"),
                "date": normalized.get("date"),
                "company": normalized.get("company"),
            },
            field_confidences=extraction.field_confidences or normalized.get("field_confidences"),
            processing_history=[
                {
                    "stage": "invoice_created",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "confidence": float(extraction.confidence or 0),
                }
            ],
        )
        return await self.invoice_repo.create(invoice)

    async def generate_invoice_number(self) -> str:
        seq = await self.invoice_repo.get_next_sequence()
        year = datetime.now(UTC).year
        return f"INV-{year}-{seq:05d}"

    async def store_pdf_metadata(
        self,
        invoice_id: UUID,
        storage_path: str,
        metadata: dict[str, Any] | None = None,
    ) -> Invoice:
        invoice = await self.invoice_repo.get_by_id(invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", str(invoice_id))

        pdf_meta = metadata or {}
        pdf_meta.setdefault("generated_at", datetime.now(UTC).isoformat())
        pdf_meta.setdefault("format", "pdf")
        pdf_meta.setdefault("confidence", invoice.confidence_score or 0)

        invoice.pdf_storage_path = storage_path
        invoice.pdf_metadata = pdf_meta
        history = list(invoice.processing_history or [])
        history.append(
            {
                "stage": "pdf_metadata_stored",
                "timestamp": datetime.now(UTC).isoformat(),
                "path": storage_path,
                "confidence": pdf_meta.get("confidence", 0),
            }
        )
        invoice.processing_history = history
        return await self.invoice_repo.update(invoice)

    def _build_line_items(self, normalized: dict, subtotal: Decimal | None) -> list[dict]:
        employee = normalized.get("employee", "Consultant")
        hours = normalized.get("hours")
        rate = normalized.get("rate")
        project = normalized.get("project", "General")

        if hours and rate:
            return [
                {
                    "description": f"{employee} - {project}",
                    "quantity": float(hours),
                    "unit_price": float(rate),
                    "amount": float(Decimal(str(hours)) * Decimal(str(rate))),
                }
            ]
        if subtotal:
            return [{"description": f"Services - {project}", "amount": float(subtotal)}]
        return []

    @staticmethod
    def _decimal(value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except Exception:
            return None

    @staticmethod
    def _parse_date(value) -> date | None:
        if not value:
            return None
        if isinstance(value, date):
            return value
        from dateutil import parser as date_parser

        try:
            return date_parser.parse(str(value)).date()
        except Exception as exc:
            raise ProcessingError(
                f"Invalid date value: {value}",
                reason=str(exc),
            ) from exc
