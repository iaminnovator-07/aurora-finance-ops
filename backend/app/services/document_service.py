"""Document upload, extraction, classification, and normalization."""

import time
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ProcessingError
from app.models.base import DocumentType
from app.models.document import DocumentExtraction
from app.repositories.email_repository import EmailAttachmentRepository
from app.repositories.misc_repository import DocumentExtractionRepository
from app.services.ai.gemini_service import GeminiService
from app.services.ocr_service import OCRService
from app.services.storage_service import StorageService


class DocumentService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = StorageService(session)
        self.ocr = OCRService(session)
        self.gemini = GeminiService(session)
        self.attachment_repo = EmailAttachmentRepository(session)
        self.extraction_repo = DocumentExtractionRepository(session)

    async def upload_file(
        self,
        filename: str,
        content: bytes,
        content_type: str,
        email_id: UUID | None = None,
    ) -> dict:
        from app.models.email import Email, EmailAttachment

        if not email_id:
            from datetime import UTC, datetime
            email = Email(
                from_email="upload@aurora-tia.local",
                from_name="Document Upload",
                to_email="ap@yourcompany.com",
                subject=f"Uploaded: {filename}",
                body_text="Document uploaded via API",
                received_at=datetime.now(UTC),
                status="received",
            )
            from app.repositories.email_repository import EmailRepository
            email = await EmailRepository(self.session).create(email)
            email_id = email.id

        attachment = await self.upload(email_id, filename, content, content_type)
        return {
            "attachment_id": attachment.id,
            "filename": attachment.filename,
            "storage_path": attachment.storage_path,
            "size_bytes": attachment.size_bytes,
        }

    async def upload(
        self,
        email_id: UUID,
        filename: str,
        content: bytes,
        content_type: str,
    ):
        from app.models.email import EmailAttachment

        storage_path = await self.storage.save_file(content, filename, subdir="attachments")
        attachment = EmailAttachment(
            email_id=email_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(content),
            storage_path=storage_path,
            checksum=StorageService.compute_checksum(content),
            is_processed=False,
        )
        return await self.attachment_repo.create(attachment)

    async def extract(self, attachment_id: UUID) -> DocumentExtraction:
        attachment = await self.attachment_repo.get_by_id(attachment_id)
        if not attachment:
            raise NotFoundError("EmailAttachment", str(attachment_id))

        existing = await self.extraction_repo.get_by_attachment_id(attachment_id)
        if existing:
            return existing

        start = time.perf_counter()
        try:
            content = await self.storage.read_file_bytes(attachment.storage_path)
            local_path = attachment.storage_path
            if attachment.storage_path.startswith("supabase://"):
                import tempfile
                from pathlib import Path

                suffix = Path(attachment.filename).suffix or ".bin"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(content)
                    local_path = tmp.name

            ocr_result = await self.ocr.extract_from_file(local_path, attachment.content_type)
        except ProcessingError:
            raise
        except Exception as exc:
            raise ProcessingError(
                "Document extraction failed",
                reason=str(exc),
            ) from exc

        doc_type = await self.classify(ocr_result["raw_text"], attachment.content_type)
        normalized = await self.normalize(ocr_result["extracted_data"], ocr_result["raw_text"])

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        extraction = DocumentExtraction(
            attachment_id=attachment_id,
            document_type=doc_type,
            raw_text=ocr_result["raw_text"],
            extracted_data=ocr_result["extracted_data"],
            normalized_data=normalized,
            confidence=float(ocr_result.get("confidence", normalized.get("confidence", 0))),
            field_confidences=normalized.get("field_confidences"),
            classification=doc_type,
            ocr_engine=ocr_result.get("ocr_engine"),
            processing_time_ms=elapsed_ms,
        )
        extraction = await self.extraction_repo.create(extraction)

        attachment.is_processed = True
        await self.attachment_repo.update(attachment)
        return extraction

    async def extract_dict(self, attachment_id: UUID) -> dict:
        ext = await self.extract(attachment_id)
        return {
            "extraction_id": ext.id,
            "document_type": ext.document_type,
            "extracted_data": ext.extracted_data,
            "confidence": ext.confidence,
            "field_confidences": ext.field_confidences or {},
            "processing_time_ms": ext.processing_time_ms or 0,
        }

    async def classify_attachment(self, attachment_id: UUID) -> dict:
        attachment = await self.attachment_repo.get_by_id(attachment_id)
        if not attachment:
            raise NotFoundError("EmailAttachment", str(attachment_id))
        content = await self.storage.read_file_bytes(attachment.storage_path)
        ocr = await self.ocr.extract_from_file(attachment.storage_path, attachment.content_type)
        doc_type = await self.classify(ocr["raw_text"], attachment.content_type)
        return {
            "classification": doc_type,
            "confidence": ocr.get("confidence", 85.0),
            "document_type": doc_type,
        }

    async def normalize_extraction(self, extraction_id: UUID) -> dict:
        ext = await self.extraction_repo.get_by_id(extraction_id)
        if not ext:
            raise NotFoundError("DocumentExtraction", str(extraction_id))
        normalized = await self.normalize(ext.extracted_data, ext.raw_text or "")
        ext.normalized_data = normalized
        await self.extraction_repo.update(ext)
        return {
            "normalized_data": normalized,
            "confidence": normalized.get("confidence", ext.confidence),
            "erp_mapping": {
                "employee": "Employee Name",
                "hours": "Quantity",
                "rate": "Unit Price",
                "date": "Posting Date",
                "company": "Vendor Account",
                "project": "Cost Center",
                "ot_hours": "OT Quantity",
                "total": "Amount",
            },
        }

    async def classify(self, raw_text: str, content_type: str) -> str:
        ct = content_type.lower()
        if "pdf" in ct:
            base_type = DocumentType.PDF.value
        elif "spreadsheet" in ct or "excel" in ct:
            base_type = DocumentType.EXCEL.value
        elif "image" in ct:
            base_type = DocumentType.IMAGE.value
        else:
            base_type = DocumentType.UNKNOWN.value

        prompt = (
            f"Classify this document as one of: invoice, timesheet, receipt, contract, other.\n"
            f"Content type: {content_type}\n\nText:\n{raw_text[:3000]}"
        )
        result = await self.gemini.generate_json(
            prompt,
            schema_hint='{"document_type": "string", "confidence": "number"}',
        )
        doc_class = result.get("document_type", "other").lower()
        mapping = {
            "invoice": DocumentType.PDF.value if base_type == DocumentType.PDF.value else base_type,
            "timesheet": DocumentType.EXCEL.value,
            "receipt": DocumentType.IMAGE.value,
        }
        return mapping.get(doc_class, base_type)

    async def normalize(self, extracted_data: dict, raw_text: str) -> dict:
        prompt = (
            "Normalize the following extracted document fields into a consistent JSON structure "
            "with keys: employee, hours, rate, date, company, project, ot_hours, subtotal, tax, total, currency. "
            "Include field_confidences map and overall confidence.\n\n"
            f"Extracted: {extracted_data}\n\nRaw text excerpt:\n{raw_text[:2000]}"
        )
        ai_result = await self.gemini.generate_json(prompt)

        normalized = {
            "employee": ai_result.get("employee") or extracted_data.get("employee"),
            "hours": self._to_float(ai_result.get("hours") or extracted_data.get("hours")),
            "rate": self._to_float(ai_result.get("rate") or extracted_data.get("rate")),
            "date": ai_result.get("date") or extracted_data.get("date"),
            "company": ai_result.get("company") or extracted_data.get("company"),
            "project": ai_result.get("project") or extracted_data.get("project"),
            "ot_hours": self._to_float(ai_result.get("ot_hours") or extracted_data.get("ot_hours")),
            "subtotal": self._to_decimal(ai_result.get("subtotal")),
            "tax": self._to_decimal(ai_result.get("tax")),
            "total": self._to_decimal(ai_result.get("total")),
            "currency": ai_result.get("currency", "USD"),
            "confidence": ai_result.get("_confidence") or ai_result.get("confidence") or extracted_data.get("confidence", 0),
            "field_confidences": ai_result.get("field_confidences", {}),
            "source": ai_result.get("_source", "ocr"),
        }

        hours = normalized.get("hours") or 0
        rate = normalized.get("rate") or 0
        if not normalized.get("subtotal") and hours and rate:
            normalized["subtotal"] = float(hours) * float(rate)
        if not normalized.get("total") and normalized.get("subtotal"):
            normalized["total"] = normalized["subtotal"]

        return normalized

    @staticmethod
    def _to_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_decimal(value) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None
