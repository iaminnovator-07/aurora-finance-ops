"""Gmail sync with API client or demo seed fallback."""

import base64
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import ProcessingError
from app.models.base import EmailStatus
from app.models.email import Email, EmailAttachment
from app.repositories.email_repository import EmailRepository
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class GmailService:
    DEMO_EMAILS = [
        {
            "from_email": "billing@acme-logistics.com",
            "from_name": "Acme Logistics",
            "subject": "Invoice #INV-2381 — October shipment",
            "body_text": "Hi Finance Team,\n\nPlease find attached invoice INV-2381 for October shipment services. Payment terms Net-30. Total due: $12,420.00.\n\n— Billing, Acme Logistics",
        },
        {
            "from_email": "ar@globex.com",
            "from_name": "Globex Materials",
            "subject": "Net-30 invoice attached",
            "body_text": "Please find attached invoice for materials. Total: $3,890.50. PO-44812.",
        },
        {
            "from_email": "finance@unknown-vendor.biz",
            "from_name": "Unknown Sender",
            "subject": "URGENT: Wire transfer required",
            "body_text": "Click here immediately to wire funds. Urgent action required.",
        },
        {
            "from_email": "ap@hooli.com",
            "from_name": "Hooli Services",
            "subject": "Re: Q3 consulting hours",
            "body_text": "Attached timesheet: Jane Doe, 140 regular hours, 10 OT hours, rate $95/hr. Total: $14,820.",
        },
        {
            "from_email": "billing@soylent.industries",
            "from_name": "Soylent Ind.",
            "subject": "Recurring invoice — auto-generated",
            "body_text": "Monthly subscription invoice attached. Amount: $540.00.",
        },
        {
            "from_email": "no-reply@initech.cloud",
            "from_name": "Initech Cloud",
            "subject": "Your monthly subscription receipt",
            "body_text": "Receipt for cloud services. Amount: $1,240.00.",
        },
    ]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.email_repo = EmailRepository(session)
        self.storage = StorageService(session)

    async def sync_emails(self, max_results: int = 20) -> dict:
        credentials = self._load_credentials()
        if credentials:
            try:
                return await self._sync_from_gmail_api(credentials, max_results)
            except Exception as exc:
                logger.warning("Gmail API sync failed, falling back to demo: %s", exc)

        return await self._sync_demo_emails(max_results)

    def _load_credentials(self) -> dict | None:
        token_path = Path(self.settings.gmail_token_path)
        if not token_path.exists():
            return None
        try:
            return json.loads(token_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("Could not load Gmail token: %s", exc)
            return None

    async def _sync_from_gmail_api(self, token_data: dict, max_results: int) -> dict:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_info(token_data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            Path(self.settings.gmail_token_path).write_text(creds.to_json(), encoding="utf-8")

        service = build("gmail", "v1", credentials=creds)
        user_id = self.settings.gmail_user_email or "me"
        results = service.users().messages().list(userId=user_id, maxResults=max_results).execute()
        messages = results.get("messages", [])

        synced = 0
        skipped = 0
        for msg_ref in messages:
            msg_id = msg_ref["id"]
            existing = await self.email_repo.get_by_gmail_id(msg_id)
            if existing:
                skipped += 1
                continue

            msg = service.users().messages().get(userId=user_id, id=msg_id, format="full").execute()
            email = await self._parse_gmail_message(msg)
            synced += 1

            for part in msg.get("payload", {}).get("parts", []):
                if part.get("filename") and part.get("body", {}).get("attachmentId"):
                    att_data = (
                        service.users()
                        .messages()
                        .attachments()
                        .get(userId=user_id, messageId=msg_id, id=part["body"]["attachmentId"])
                        .execute()
                    )
                    content = base64.urlsafe_b64decode(att_data["data"])
                    storage_path = await self.storage.save_file(
                        content, part["filename"], subdir="attachments"
                    )
                    attachment = EmailAttachment(
                        email_id=email.id,
                        filename=part["filename"],
                        content_type=part.get("mimeType", "application/octet-stream"),
                        size_bytes=len(content),
                        storage_path=storage_path,
                        checksum=StorageService.compute_checksum(content),
                    )
                    self.session.add(attachment)

        await self.session.flush()
        return {
            "source": "gmail_api",
            "synced": synced,
            "skipped": skipped,
            "confidence": 95.0,
        }

    async def _parse_gmail_message(self, msg: dict) -> Email:
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        from_raw = headers.get("from", "")
        from_email = from_raw
        from_name = None
        if "<" in from_raw:
            from_name = from_raw.split("<")[0].strip().strip('"')
            from_email = from_raw.split("<")[1].strip(">")

        body_text = self._extract_body(msg.get("payload", {}))
        internal_date = int(msg.get("internalDate", 0)) / 1000
        received_at = datetime.fromtimestamp(internal_date, tz=UTC) if internal_date else datetime.now(UTC)

        email = Email(
            gmail_message_id=msg["id"],
            thread_id=msg.get("threadId"),
            from_email=from_email,
            from_name=from_name,
            to_email=headers.get("to", self.settings.gmail_user_email or "inbox@aurora.local"),
            subject=headers.get("subject", "(no subject)"),
            body_text=body_text,
            received_at=received_at,
            status=EmailStatus.RECEIVED.value,
            raw_headers=headers,
        )
        return await self.email_repo.create(email)

    def _extract_body(self, payload: dict) -> str:
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
        return ""

    async def _sync_demo_emails(self, max_results: int) -> dict:
        synced = 0
        to_email = self.settings.gmail_user_email or "inbox@aurora.local"

        for idx, demo in enumerate(self.DEMO_EMAILS[:max_results]):
            gmail_id = f"demo-{uuid4().hex[:12]}"
            existing = await self.email_repo.get_by_gmail_id(gmail_id)
            if existing:
                continue

            email = Email(
                gmail_message_id=gmail_id,
                from_email=demo["from_email"],
                from_name=demo["from_name"],
                to_email=to_email,
                subject=demo["subject"],
                body_text=demo["body_text"],
                received_at=datetime.now(UTC) - timedelta(hours=idx),
                status=EmailStatus.RECEIVED.value,
            )
            email = await self.email_repo.create(email)

            demo_content = demo["body_text"].encode("utf-8")
            storage_path = await self.storage.save_file(
                demo_content, f"demo_timesheet_{idx}.txt", subdir="attachments"
            )
            attachment = EmailAttachment(
                email_id=email.id,
                filename=f"demo_timesheet_{idx}.txt",
                content_type="text/plain",
                size_bytes=len(demo_content),
                storage_path=storage_path,
                checksum=StorageService.compute_checksum(demo_content),
            )
            self.session.add(attachment)
            synced += 1

        await self.session.flush()
        return {
            "source": "demo_seed",
            "synced": synced,
            "skipped": 0,
            "confidence": 70.0,
            "reason": "Gmail credentials not configured; ingested demo emails",
        }
