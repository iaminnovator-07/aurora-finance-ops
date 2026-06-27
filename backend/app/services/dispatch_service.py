"""Invoice dispatch via email with attachment tracking."""

import logging
import smtplib
import uuid
from datetime import UTC, datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import NotFoundError, ProcessingError
from app.models.audit import DispatchRecord
from app.models.base import DispatchStatus, InvoiceStatus, NotificationType
from app.repositories.base import BaseRepository
from app.repositories.invoice_repository import InvoiceRepository
from app.services.notification_service import NotificationService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DispatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.invoice_repo = InvoiceRepository(session)
        self.dispatch_repo = BaseRepository(session, DispatchRecord)
        self.storage = StorageService(session)
        self.notifications = NotificationService(session)

    async def prepare_dispatch(
        self,
        invoice_id: UUID,
        recipient_email: str,
        *,
        subject: str | None = None,
        body: str | None = None,
    ) -> DispatchRecord:
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", str(invoice_id))

        attachment_paths: list[str] = []
        if invoice.pdf_storage_path:
            attachment_paths.append(invoice.pdf_storage_path)

        for export in invoice.erp_exports or []:
            if export.file_path:
                attachment_paths.append(export.file_path)

        dispatch = DispatchRecord(
            invoice_id=invoice_id,
            recipient_email=recipient_email,
            subject=subject or f"Invoice {invoice.invoice_number} from Aurora TIA",
            body=body
            or (
                f"Dear Client,\n\n"
                f"Please find attached invoice {invoice.invoice_number} "
                f"for {invoice.vendor_name or 'services'}.\n\n"
                f"Total: {invoice.currency} {invoice.total_amount}\n\n"
                f"Regards,\nAurora TIA"
            ),
            status=DispatchStatus.PREPARED.value,
            attachment_paths=attachment_paths,
            tracking_id=f"AUR-{uuid.uuid4().hex[:12].upper()}",
            metadata_json={
                "invoice_number": invoice.invoice_number,
                "confidence": invoice.confidence_score,
            },
        )
        return await self.dispatch_repo.create(dispatch)

    async def send_dispatch(self, dispatch_id: UUID) -> DispatchRecord:
        dispatch = await self.dispatch_repo.get_by_id(dispatch_id)
        if not dispatch:
            raise NotFoundError("DispatchRecord", str(dispatch_id))

        invoice = await self.invoice_repo.get_by_id(dispatch.invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", str(dispatch.invoice_id))

        try:
            await self._send_email(dispatch)
            dispatch.status = DispatchStatus.SENT.value
            dispatch.sent_at = datetime.now(UTC)
        except Exception as exc:
            logger.error("Dispatch send failed: %s", exc)
            dispatch.status = DispatchStatus.FAILED.value
            dispatch.error_message = str(exc)
            await self.dispatch_repo.update(dispatch)
            raise ProcessingError(
                "Failed to send dispatch email",
                reason=str(exc),
            ) from exc

        await self.dispatch_repo.update(dispatch)

        invoice.status = InvoiceStatus.DISPATCHED.value
        invoice.dispatched_at = datetime.now(UTC)
        await self.invoice_repo.update(invoice)

        await self.notifications.create_notification(
            type=NotificationType.DISPATCH_COMPLETED.value,
            title=f"Invoice {invoice.invoice_number} dispatched",
            message=f"Sent to {dispatch.recipient_email}",
            entity_type="invoice",
            entity_id=str(invoice.id),
        )
        return dispatch

    async def _send_email(self, dispatch: DispatchRecord) -> None:
        msg = MIMEMultipart()
        msg["Subject"] = dispatch.subject
        msg["From"] = self.settings.gmail_user_email or "noreply@aurora-tia.local"
        msg["To"] = dispatch.recipient_email
        msg.attach(MIMEText(dispatch.body, "plain"))

        for path in dispatch.attachment_paths or []:
            try:
                content = await self.storage.read_file_bytes(path)
                filename = path.split("/")[-1].split("\\")[-1]
                part = MIMEApplication(content, Name=filename)
                part["Content-Disposition"] = f'attachment; filename="{filename}"'
                msg.attach(part)
            except Exception as exc:
                logger.warning("Could not attach file %s: %s", path, exc)

        if self.settings.environment == "development":
            logger.info(
                "Development mode: simulated email send to %s (tracking: %s)",
                dispatch.recipient_email,
                dispatch.tracking_id,
            )
            dispatch.status = DispatchStatus.DELIVERED.value
            dispatch.delivered_at = datetime.now(UTC)
            return

        with smtplib.SMTP("localhost", 25, timeout=10) as server:
            server.send_message(msg)
        dispatch.delivered_at = datetime.now(UTC)

    async def send_invoice(
        self,
        invoice_id: UUID,
        recipient_email: str | None = None,
        custom_message: str | None = None,
        user_id: UUID | None = None,
    ) -> dict:
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", str(invoice_id))

        recipient = recipient_email or (invoice.client.email if invoice.client else None)
        if not recipient:
            raise ProcessingError("No recipient email available", reason="Missing recipient")

        dispatch = await self.prepare_dispatch(
            invoice_id, recipient, body=custom_message
        )
        dispatch = await self.send_dispatch(dispatch.id)
        return {
            "dispatch_id": dispatch.id,
            "status": dispatch.status,
            "recipient_email": dispatch.recipient_email,
            "subject": dispatch.subject,
            "tracking_id": dispatch.tracking_id,
        }
