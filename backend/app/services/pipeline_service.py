"""End-to-end email processing pipeline orchestrator."""

import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import NotFoundError, ProcessingError
from app.models.audit import AgentRunLog
from app.models.base import EmailStatus, InvoiceStatus, NotificationType
from app.repositories.base import BaseRepository
from app.repositories.email_repository import EmailAttachmentRepository, EmailRepository
from app.repositories.misc_repository import ClientRepository
from app.services.analytics_service import AnalyticsService
from app.services.approval_service import ApprovalService
from app.services.audit_service import AuditService
from app.services.dispatch_service import DispatchService
from app.services.document_service import DocumentService
from app.services.erp_service import ERPService
from app.services.invoice_service import InvoiceService
from app.services.mail_intelligence_service import MailIntelligenceService
from app.services.notification_service import NotificationService
from app.services.rule_engine_service import RuleEngineService
from app.services.trust_engine_service import TrustEngineService

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.email_repo = EmailRepository(session)
        self.attachment_repo = EmailAttachmentRepository(session)
        self.client_repo = ClientRepository(session)
        self.agent_log_repo = BaseRepository(session, AgentRunLog)

        self.mail_intel = MailIntelligenceService(session)
        self.trust_engine = TrustEngineService(session)
        self.document = DocumentService(session)
        self.invoice = InvoiceService(session)
        self.rules = RuleEngineService(session)
        self.approval = ApprovalService(session)
        self.erp = ERPService(session)
        self.dispatch = DispatchService(session)
        self.analytics = AnalyticsService(session)
        self.notifications = NotificationService(session)
        self.audit = AuditService(session)

    async def process_email(self, email_id: UUID) -> dict:
        start = time.perf_counter()
        email = await self.email_repo.get_with_details(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        email.status = EmailStatus.PROCESSING.value
        email.processing_started_at = datetime.now(UTC)
        email.pipeline_stage = "started"
        await self.email_repo.update(email)

        result: dict = {"email_id": str(email_id), "stages": {}, "confidence": 0.0}

        try:
            # Stage 1: Mail intelligence (summary, intent, priority, spam)
            intel = await self._run_stage("mail_intelligence", email_id, self.mail_intel.analyze_email, email_id)
            result["stages"]["mail_intelligence"] = intel

            if intel.get("spam", {}).get("is_spam"):
                email.status = EmailStatus.SPAM.value
                email.is_spam = True
                email.pipeline_stage = "spam_detected"
                await self.email_repo.update(email)
                result["outcome"] = "spam_rejected"
                result["confidence"] = intel.get("confidence", 0)
                return await self._finalize(email, result, start)

            # Resolve client from sender domain
            client = await self.client_repo.get_by_email_domain(email.from_email)
            if client:
                email.client_id = client.id

            # Stage 2: Trust scoring
            trust = await self._run_stage("trust_engine", email_id, self.trust_engine.check_email, email_id)
            result["stages"]["trust"] = {
                "overall_score": trust.overall_score,
                "risk_level": trust.risk_level,
                "confidence": 90.0,
            }

            # Stage 3: OCR + document extraction
            extractions = []
            attachments = await self.attachment_repo.get_by_email_id(email_id)
            for attachment in attachments:
                extraction = await self._run_stage(
                    "document_extraction",
                    email_id,
                    self.document.extract,
                    attachment.id,
                )
                extractions.append(extraction)

            result["stages"]["extractions"] = [
                {"id": str(e.id), "confidence": e.confidence, "type": e.document_type}
                for e in extractions
            ]

            if not extractions:
                result["outcome"] = "no_attachments"
                result["confidence"] = trust.overall_score
                email.pipeline_stage = "no_attachments"
                await self.email_repo.update(email)
                return await self._finalize(email, result, start)

            # Stage 4: Invoice creation from best extraction
            best = max(extractions, key=lambda e: e.confidence or 0)
            invoice = await self._run_stage(
                "invoice_creation",
                email_id,
                self.invoice.create_from_extraction,
                best.id,
                email_id,
                email.client_id,
                trust.overall_score,
            )
            result["stages"]["invoice"] = {
                "id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "confidence": invoice.confidence_score,
            }

            # Stage 5: Rule engine validation
            rules_result = await self._run_stage(
                "rule_engine", email_id, self.rules.validate_invoice, invoice.id
            )
            result["stages"]["rules"] = {
                "passed": rules_result["passed"],
                "failed_count": rules_result["failed_count"],
                "confidence": rules_result["confidence"],
            }

            # Stage 6: Approval decision
            auto_approve = (
                rules_result["passed"]
                and trust.overall_score >= self.settings.trust_auto_approve_threshold
                and (invoice.confidence_score or 0) >= self.settings.confidence_auto_approve_threshold
            )

            if auto_approve:
                invoice.status = InvoiceStatus.AUTO_APPROVED.value
                await self.invoice.invoice_repo.update(invoice)
                result["stages"]["approval"] = {"action": "auto_approved", "confidence": 95.0}
            else:
                failed_rules = [r for r in rules_result["rules"] if not r["passed"]]
                await self.approval.request_review(
                    invoice.id,
                    reason=self._build_review_reason(trust, rules_result),
                    risk_level=trust.risk_level,
                    failed_rules=failed_rules,
                    confidence_score=invoice.confidence_score,
                    trust_score=trust.overall_score,
                    ai_suggestion=self._build_suggestion(failed_rules),
                    priority=10 if trust.risk_level == "high" else 5,
                )
                result["stages"]["approval"] = {"action": "queued_for_review", "confidence": 85.0}

            # Stage 7: ERP export (for approved invoices)
            if auto_approve or invoice.status == InvoiceStatus.AUTO_APPROVED.value:
                erp_export = await self._run_stage(
                    "erp_export", email_id, self.erp.export_invoice, invoice.id
                )
                result["stages"]["erp"] = {
                    "export_id": str(erp_export.id),
                    "file_path": erp_export.file_path,
                    "confidence": 92.0,
                }

                # Stage 8: Dispatch
                recipient = email.to_email
                if client and client.email:
                    recipient = client.email
                dispatch = await self.dispatch.prepare_dispatch(invoice.id, recipient)
                sent = await self._run_stage(
                    "dispatch", email_id, self.dispatch.send_dispatch, dispatch.id
                )
                result["stages"]["dispatch"] = {
                    "dispatch_id": str(sent.id),
                    "status": sent.status,
                    "tracking_id": sent.tracking_id,
                    "confidence": 90.0,
                }

            # Stage 9: Analytics snapshot
            await self._run_stage("analytics", email_id, self.analytics.save_snapshot)
            result["stages"]["analytics"] = {"snapshot_saved": True, "confidence": 88.0}

            # Stage 10: Notifications
            await self.notifications.create_notification(
                type=NotificationType.PROCESSING_COMPLETE.value,
                title=f"Email processed: {email.subject[:60]}",
                message=f"Invoice {invoice.invoice_number} - outcome: {result.get('outcome', 'completed')}",
                entity_type="email",
                entity_id=str(email_id),
            )
            result["stages"]["notification"] = {"sent": True, "confidence": 99.0}

            result["outcome"] = "auto_approved" if auto_approve else "manual_review"
            confidences = [
                s.get("confidence", 0)
                for s in result["stages"].values()
                if isinstance(s, dict) and "confidence" in s
            ]
            result["confidence"] = round(sum(confidences) / max(len(confidences), 1), 2)

            email.status = EmailStatus.PROCESSED.value
            email.pipeline_stage = "completed"
            return await self._finalize(email, result, start)

        except Exception as exc:
            email.status = EmailStatus.FAILED.value
            email.pipeline_stage = "failed"
            email.pipeline_metadata = {"error": str(exc), "reason": getattr(exc, "reason", str(exc))}
            await self.email_repo.update(email)
            await self._log_agent("pipeline", "error", str(email_id), str(exc), 0)
            raise ProcessingError(
                f"Pipeline failed for email {email_id}",
                reason=getattr(exc, "reason", str(exc)),
            ) from exc

    async def _run_stage(self, stage: str, email_id: UUID, func, *args, **kwargs):
        stage_start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            duration_ms = int((time.perf_counter() - stage_start) * 1000)
            await self._log_agent(stage, "active", str(email_id), f"Stage {stage} completed", 90.0, duration_ms)
            return result
        except Exception as exc:
            await self._log_agent(stage, "error", str(email_id), str(exc), 0)
            raise

    async def _finalize(self, email, result: dict, start: float) -> dict:
        email.processing_completed_at = datetime.now(UTC)
        email.pipeline_metadata = result
        await self.email_repo.update(email)
        await self.audit.log_action(
            user_id=None,
            action="pipeline_complete",
            module="pipeline",
            entity_type="email",
            entity_id=str(email.id),
            new_value={"outcome": result.get("outcome")},
            details=f"Pipeline completed in {int((time.perf_counter() - start) * 1000)}ms",
            confidence=result.get("confidence"),
        )
        return result

    async def _log_agent(
        self,
        agent_name: str,
        status: str,
        entity_id: str,
        message: str,
        confidence: float,
        duration_ms: int | None = None,
    ) -> None:
        log = AgentRunLog(
            agent_name=agent_name,
            status=status,
            entity_type="email",
            entity_id=entity_id,
            confidence=confidence,
            duration_ms=duration_ms,
            message=message,
        )
        await self.agent_log_repo.create(log)

    @staticmethod
    def _build_review_reason(trust, rules_result: dict) -> str:
        parts = [f"Trust score {trust.overall_score} ({trust.risk_level} risk)"]
        if not rules_result["passed"]:
            failed = [r["rule_name"] for r in rules_result["rules"] if not r["passed"]]
            parts.append(f"Failed rules: {', '.join(failed)}")
        return "; ".join(parts)

    @staticmethod
    def _build_suggestion(failed_rules: list) -> str:
        if not failed_rules:
            return "Review recommended due to trust/confidence thresholds"
        suggestions = [r.get("suggestion") for r in failed_rules if r.get("suggestion")]
        return "; ".join(suggestions[:3]) if suggestions else "Verify invoice details manually"
