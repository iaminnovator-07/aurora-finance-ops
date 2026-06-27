"""Thin controllers — translate HTTP to service calls."""

from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    ApprovalItem,
    CopilotChatRequest,
    CopilotChatResponse,
    DashboardMetrics,
    DispatchEmailRequest,
    DispatchResponse,
    DocumentClassifyResponse,
    DocumentExtractResponse,
    DocumentNormalizeResponse,
    DocumentUploadResponse,
    EmailDetailResponse,
    EmailListItem,
    EmailProcessRequest,
    EmailProcessResponse,
    EmailSyncResponse,
    ERPExportRequest,
    ERPExportResponse,
    InvoiceCreateRequest,
    InvoiceListResponse,
    InvoiceResponse,
    MonthlyAnalytics,
    ROIAnalytics,
    RuleValidationRequest,
    RuleValidationResponse,
    TokenResponse,
    TrustCheckRequest,
    TrustCheckResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.analytics_service import AnalyticsService
from app.services.approval_service import ApprovalService
from app.services.auth_service import AuthService
from app.services.copilot_service import CopilotService
from app.services.dispatch_service import DispatchService
from app.services.document_service import DocumentService
from app.services.erp_service import ERPService
from app.services.gmail_service import GmailService
from app.services.invoice_service import InvoiceService
from app.services.pipeline_service import PipelineService
from app.services.rule_engine_service import RuleEngineService
from app.services.trust_engine_service import TrustEngineService


class AuthController:
    def __init__(self, session: AsyncSession):
        self.service = AuthService(session)

    async def register(self, data: UserRegisterRequest) -> tuple[UserResponse, TokenResponse]:
        user, tokens = await self.service.register(data.email, data.password, data.full_name)
        return UserResponse.model_validate(user), TokenResponse(**tokens)

    async def login(self, data: UserLoginRequest) -> tuple[UserResponse, TokenResponse]:
        user, tokens = await self.service.login(data.email, data.password)
        return UserResponse.model_validate(user), TokenResponse(**tokens)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        tokens = await self.service.refresh(refresh_token)
        return TokenResponse(**tokens)


class InboxController:
    def __init__(self, session: AsyncSession):
        self.gmail = GmailService(session)
        self.pipeline = PipelineService(session)
        from app.repositories.email_repository import EmailRepository

        self.email_repo = EmailRepository(session)

    async def list_emails(
        self, unread_only: bool = False, flagged_only: bool = False, limit: int = 50, offset: int = 0
    ) -> tuple[list[EmailListItem], int]:
        emails, total = await self.email_repo.list_emails(
            unread_only=unread_only, flagged_only=flagged_only, limit=limit, offset=offset
        )
        items = []
        for e in emails:
            trust = e.trust_score.overall_score if e.trust_score else None
            items.append(
                EmailListItem(
                    id=e.id,
                    from_email=e.from_email,
                    from_name=e.from_name,
                    subject=e.subject,
                    received_at=e.received_at,
                    status=e.status,
                    priority=e.priority,
                    intent=e.intent,
                    ai_summary=e.ai_summary,
                    is_read=e.is_read,
                    is_flagged=e.is_flagged,
                    is_spam=e.is_spam,
                    is_duplicate=e.is_duplicate,
                    trust_score=trust,
                    attachment_count=len(e.attachments),
                    pipeline_stage=e.pipeline_stage,
                )
            )
        return items, total

    async def get_email(self, email_id: UUID) -> EmailDetailResponse:
        from app.core.exceptions import NotFoundError

        email = await self.email_repo.get_with_details(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        trust_details = None
        suggested_action = None
        trust_score = None

        if email.trust_score:
            ts = email.trust_score
            trust_score = ts.overall_score
            trust_details = {
                "identity_score": ts.identity_score,
                "content_score": ts.content_score,
                "checks": ts.checks,
                "reasoning_timeline": ts.reasoning_timeline,
                "risk_level": ts.risk_level,
            }
            if ts.overall_score >= 80:
                suggested_action = "Auto-approve and push to ERP."
            elif ts.overall_score >= 60:
                suggested_action = "Send to manual review queue."
            else:
                suggested_action = "Reject — high fraud likelihood."

        return EmailDetailResponse(
            id=email.id,
            from_email=email.from_email,
            from_name=email.from_name,
            subject=email.subject,
            received_at=email.received_at,
            status=email.status,
            priority=email.priority,
            intent=email.intent,
            ai_summary=email.ai_summary,
            is_read=email.is_read,
            is_flagged=email.is_flagged,
            is_spam=email.is_spam,
            is_duplicate=email.is_duplicate,
            trust_score=trust_score,
            attachment_count=len(email.attachments),
            pipeline_stage=email.pipeline_stage,
            body_text=email.body_text,
            body_html=email.body_html,
            attachments=[
                {
                    "id": a.id,
                    "filename": a.filename,
                    "content_type": a.content_type,
                    "size_bytes": a.size_bytes,
                    "is_processed": a.is_processed,
                }
                for a in email.attachments
            ],
            trust_details=trust_details,
            rule_checks=None,
            suggested_action=suggested_action,
        )

    async def sync_emails(self) -> EmailSyncResponse:
        result = await self.gmail.sync_emails()
        return EmailSyncResponse(
            synced_count=result.get("synced", 0) + result.get("skipped", 0),
            new_count=result.get("synced", 0),
            duplicate_count=result.get("skipped", 0),
            message=result.get("reason", f"Synced {result.get('synced', 0)} new emails from {result.get('source', 'inbox')}"),
        )

    async def process_emails(self, data: EmailProcessRequest, user_id: UUID | None) -> EmailProcessResponse:
        from app.workers.tasks import process_all_pending_task, process_email_task

        task_ids = []
        if data.process_all:
            task = process_all_pending_task.delay()
            task_ids.append(task.id)
            return EmailProcessResponse(
                task_ids=task_ids,
                processed_count=0,
                message="Background pipeline started for all pending emails",
            )

        email_ids = data.email_ids or []
        for eid in email_ids:
            task = process_email_task.delay(str(eid))
            task_ids.append(task.id)

        return EmailProcessResponse(
            task_ids=task_ids,
            processed_count=len(email_ids),
            message=f"Pipeline started for {len(email_ids)} email(s)",
        )


class TrustController:
    def __init__(self, session: AsyncSession):
        self.service = TrustEngineService(session)

    async def check(self, data: TrustCheckRequest) -> TrustCheckResponse:
        if data.email_id:
            result = await self.service.check_email_dict(data.email_id)
        else:
            result = await self.service.check_adhoc(
                from_email=data.from_email or "",
                subject=data.subject or "",
                body=data.body or "",
            )
        return TrustCheckResponse(**result)


class DocumentController:
    def __init__(self, session: AsyncSession):
        self.service = DocumentService(session)

    async def upload(self, file: UploadFile, email_id: UUID | None) -> DocumentUploadResponse:
        content = await file.read()
        result = await self.service.upload_file(
            filename=file.filename or "upload.bin",
            content=content,
            content_type=file.content_type or "application/octet-stream",
            email_id=email_id,
        )
        return DocumentUploadResponse(**result)

    async def extract(self, attachment_id: UUID) -> DocumentExtractResponse:
        result = await self.service.extract_dict(attachment_id)
        return DocumentExtractResponse(**result)

    async def classify(self, attachment_id: UUID) -> DocumentClassifyResponse:
        result = await self.service.classify_attachment(attachment_id)
        return DocumentClassifyResponse(**result)

    async def normalize(self, extraction_id: UUID) -> DocumentNormalizeResponse:
        result = await self.service.normalize_extraction(extraction_id)
        return DocumentNormalizeResponse(**result)


class RuleController:
    def __init__(self, session: AsyncSession):
        self.service = RuleEngineService(session)

    async def validate(self, data: RuleValidationRequest) -> RuleValidationResponse:
        if data.invoice_id:
            result = await self.service.validate_invoice(data.invoice_id)
        elif data.email_id:
            result = await self.service.validate_email(data.email_id)
        elif data.data:
            result = await self.service.validate_data(data.data)
        else:
            from app.core.exceptions import ValidationError
            raise ValidationError("Provide invoice_id, email_id, or data")
        return RuleValidationResponse(**result)


class ERPController:
    def __init__(self, session: AsyncSession):
        self.service = ERPService(session)

    async def export(self, data: ERPExportRequest, user_id: UUID | None) -> ERPExportResponse:
        result = await self.service.export_invoice_response(data.invoice_id, user_id, data.format)
        return ERPExportResponse(**result)


class InvoiceController:
    def __init__(self, session: AsyncSession):
        self.service = InvoiceService(session)

    async def create(self, data: InvoiceCreateRequest) -> InvoiceResponse:
        invoice = await self.service.create_from_extraction(
            email_id=data.email_id,
            extraction_id=data.extraction_id,
            client_id=data.client_id,
        )
        return InvoiceResponse.model_validate(invoice)

    async def list_invoices(
        self, status: str | None = None, search: str | None = None, limit: int = 50, offset: int = 0
    ) -> InvoiceListResponse:
        from app.repositories.invoice_repository import InvoiceRepository

        repo = InvoiceRepository(self.service.session)
        items, total = await repo.list_invoices(status=status, search=search, limit=limit, offset=offset)
        return InvoiceListResponse(
            items=[InvoiceResponse.model_validate(i) for i in items],
            total=total,
        )

    async def get_invoice(self, invoice_id: UUID) -> InvoiceResponse:
        from app.core.exceptions import NotFoundError
        from app.repositories.invoice_repository import InvoiceRepository

        repo = InvoiceRepository(self.service.session)
        invoice = await repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", str(invoice_id))
        return InvoiceResponse.model_validate(invoice)


class ApprovalController:
    def __init__(self, session: AsyncSession):
        self.service = ApprovalService(session)

    async def list_approvals(self, status: str | None = None) -> list[ApprovalItem]:
        items = await self.service.list_queue_dicts(status=status)
        return [ApprovalItem(**item) for item in items]

    async def approve(self, approval_id: UUID, user_id: UUID, data: ApprovalActionRequest) -> ApprovalActionResponse:
        result = await self.service.approve_response(approval_id, user_id, data.notes)
        return ApprovalActionResponse(**result)

    async def reject(self, approval_id: UUID, user_id: UUID, data: ApprovalActionRequest) -> ApprovalActionResponse:
        result = await self.service.reject_response(approval_id, user_id, data.notes)
        return ApprovalActionResponse(**result)

    async def request_review(
        self, approval_id: UUID, user_id: UUID, data: ApprovalActionRequest
    ) -> ApprovalActionResponse:
        result = await self.service.request_review_response(approval_id, user_id, data.notes)
        return ApprovalActionResponse(**result)


class DispatchController:
    def __init__(self, session: AsyncSession):
        self.service = DispatchService(session)

    async def send_email(self, data: DispatchEmailRequest, user_id: UUID | None) -> DispatchResponse:
        result = await self.service.send_invoice(
            invoice_id=data.invoice_id,
            recipient_email=str(data.recipient_email) if data.recipient_email else None,
            custom_message=data.custom_message,
            user_id=user_id,
        )
        return DispatchResponse(**result)


class AnalyticsController:
    def __init__(self, session: AsyncSession):
        self.service = AnalyticsService(session)

    async def dashboard(self) -> DashboardMetrics:
        data = await self.service.get_dashboard()
        return DashboardMetrics(**data)

    async def monthly(self) -> MonthlyAnalytics:
        data = await self.service.get_monthly()
        return MonthlyAnalytics(**data)

    async def roi(self) -> ROIAnalytics:
        data = await self.service.get_roi()
        return ROIAnalytics(**data)


class CopilotController:
    def __init__(self, session: AsyncSession):
        self.service = CopilotService(session)

    async def chat(self, user_id: UUID, data: CopilotChatRequest) -> CopilotChatResponse:
        result = await self.service.chat(user_id, data.message, data.conversation_id)
        return CopilotChatResponse(**result)
