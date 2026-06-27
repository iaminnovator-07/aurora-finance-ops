"""Pydantic request/response schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AuroraSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserResponse(AuroraSchema):
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool


# ── Common ────────────────────────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Any = None
    confidence: float | None = None


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str
    reason: str
    details: dict[str, Any] | None = None


# ── Email / Inbox ─────────────────────────────────────────────────────────────

class EmailAttachmentResponse(AuroraSchema):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    is_processed: bool


class EmailListItem(AuroraSchema):
    id: UUID
    from_email: str
    from_name: str | None
    subject: str
    received_at: datetime
    status: str
    priority: str
    intent: str | None
    ai_summary: str | None
    is_read: bool
    is_flagged: bool
    is_spam: bool
    is_duplicate: bool
    trust_score: float | None = None
    attachment_count: int = 0
    pipeline_stage: str | None = None


class EmailDetailResponse(EmailListItem):
    body_text: str | None
    body_html: str | None
    attachments: list[EmailAttachmentResponse] = []
    trust_details: dict[str, Any] | None = None
    rule_checks: list[dict[str, Any]] | None = None
    suggested_action: str | None = None


class EmailSyncResponse(BaseModel):
    synced_count: int
    new_count: int
    duplicate_count: int
    message: str


class EmailProcessRequest(BaseModel):
    email_ids: list[UUID] | None = None
    process_all: bool = False


class EmailProcessResponse(BaseModel):
    task_ids: list[str]
    processed_count: int
    message: str


# ── Trust ─────────────────────────────────────────────────────────────────────

class TrustCheckRequest(BaseModel):
    email_id: UUID | None = None
    from_email: str | None = None
    subject: str | None = None
    body: str | None = None


class TrustCheckResponse(BaseModel):
    trust_score: float
    identity_score: float
    content_score: float
    domain_trust_score: float
    vendor_reputation_score: float
    duplicate_score: float
    overall_score: float
    risk_level: str
    reason: str
    checks: dict[str, Any]
    reasoning_timeline: list[dict[str, Any]]
    confidence: float


# ── Documents ─────────────────────────────────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    attachment_id: UUID
    filename: str
    storage_path: str
    size_bytes: int


class DocumentExtractResponse(BaseModel):
    extraction_id: UUID
    document_type: str
    extracted_data: dict[str, Any]
    confidence: float
    field_confidences: dict[str, float]
    processing_time_ms: int


class DocumentClassifyResponse(BaseModel):
    classification: str
    confidence: float
    document_type: str


class DocumentNormalizeResponse(BaseModel):
    normalized_data: dict[str, Any]
    confidence: float
    erp_mapping: dict[str, str]


# ── Rules ─────────────────────────────────────────────────────────────────────

class RuleValidationRequest(BaseModel):
    invoice_id: UUID | None = None
    email_id: UUID | None = None
    data: dict[str, Any] | None = None


class RuleResult(BaseModel):
    rule_name: str
    category: str
    passed: bool
    severity: str
    reason: str
    suggestion: str | None = None
    confidence: float = 100.0


class RuleValidationResponse(BaseModel):
    passed: bool
    total_rules: int
    passed_count: int
    failed_count: int
    results: list[RuleResult]
    confidence: float


# ── ERP ───────────────────────────────────────────────────────────────────────

class ERPExportRequest(BaseModel):
    invoice_id: UUID
    format: str = "sap_excel"


class ERPExportResponse(BaseModel):
    export_id: UUID
    file_path: str
    download_url: str
    row_count: int
    format: str


# ── Invoice ───────────────────────────────────────────────────────────────────

class InvoiceCreateRequest(BaseModel):
    email_id: UUID | None = None
    extraction_id: UUID | None = None
    client_id: UUID | None = None


class InvoiceResponse(AuroraSchema):
    id: UUID
    invoice_number: str
    status: str
    vendor_name: str | None
    issue_date: date | None
    due_date: date | None
    po_reference: str | None
    currency: str
    subtotal: Decimal | None
    tax_amount: Decimal | None
    total_amount: Decimal | None
    trust_score: float | None
    confidence_score: float | None
    line_items: list[dict[str, Any]] | None
    extracted_fields: dict[str, Any] | None
    field_confidences: dict[str, float] | None
    processing_history: list[dict[str, Any]]
    rules_passed: bool | None
    created_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int


# ── Approval ──────────────────────────────────────────────────────────────────

class ApprovalItem(AuroraSchema):
    id: UUID
    invoice_id: UUID
    invoice_number: str | None = None
    status: str
    approval_status: str
    reason: str
    risk_level: str
    ai_recommendation: str | None
    ai_suggestion: str | None
    confidence_score: float | None
    trust_score: float | None
    failed_rules: list[dict[str, Any]] | None
    assignee_name: str | None = None
    created_at: datetime


class ApprovalActionRequest(BaseModel):
    notes: str | None = None


class ApprovalActionResponse(BaseModel):
    approval_id: UUID
    invoice_id: UUID
    status: str
    message: str
    next_stage: str | None = None


# ── Dispatch ──────────────────────────────────────────────────────────────────

class DispatchEmailRequest(BaseModel):
    invoice_id: UUID
    recipient_email: EmailStr | None = None
    custom_message: str | None = None


class DispatchResponse(BaseModel):
    dispatch_id: UUID
    status: str
    recipient_email: str
    subject: str
    tracking_id: str | None = None


# ── Analytics ─────────────────────────────────────────────────────────────────

class DashboardMetrics(BaseModel):
    processed_today: int
    auto_approved: int
    pending_review: int
    fraud_alerts: int
    trust_avg: float
    ai_accuracy: float
    touchless_percentage: float
    hours_saved_today: float
    recent_invoices: list[dict[str, Any]]
    throughput_trend: list[dict[str, Any]]
    vendor_breakdown: list[dict[str, Any]]
    approval_breakdown: list[dict[str, Any]]
    agent_status: list[dict[str, Any]]


class MonthlyAnalytics(BaseModel):
    months: list[str]
    invoices: list[int]
    savings_usd: list[float]
    hours_saved: list[float]
    fraud_prevented: list[float]
    by_department: list[dict[str, Any]]
    fraud_heatmap: list[dict[str, Any]]


class ROIAnalytics(BaseModel):
    hours_saved_month: float
    dollars_saved_month: float
    fraud_prevented_ytd: float
    roi_multiplier: float
    touchless_rate: float
    avg_processing_time_seconds: float
    pending_reviews: int


# ── Copilot ───────────────────────────────────────────────────────────────────

class CopilotChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None


class CopilotChatResponse(BaseModel):
    conversation_id: UUID
    reply: str
    data: dict[str, Any] | None = None
    confidence: float
    sources: list[dict[str, str]] | None = None


# ── Clients ───────────────────────────────────────────────────────────────────

class ClientResponse(AuroraSchema):
    id: UUID
    name: str
    domain: str | None
    email: str | None
    phone: str | None
    city: str | None
    country: str | None
    is_active: bool
    trust_score: float | None = None
    invoice_count: int = 0
    spend_ytd: float = 0.0
    risk_level: str = "medium"


# ── Agents ────────────────────────────────────────────────────────────────────

class AgentStatusResponse(BaseModel):
    agents: list[dict[str, Any]]
    pipeline_running: bool
    live_logs: list[dict[str, Any]]
