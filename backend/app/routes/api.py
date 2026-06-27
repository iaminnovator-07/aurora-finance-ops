"""API route definitions — no business logic here."""

from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.controllers import (
    AnalyticsController,
    ApprovalController,
    AuthController,
    CopilotController,
    DispatchController,
    DocumentController,
    ERPController,
    InboxController,
    InvoiceController,
    RuleController,
    TrustController,
)
from app.core.dependencies import CurrentUser, DbSession
from app.schemas import (
    APIResponse,
    ApprovalActionRequest,
    CopilotChatRequest,
    DispatchEmailRequest,
    ERPExportRequest,
    EmailProcessRequest,
    InvoiceCreateRequest,
    RefreshTokenRequest,
    RuleValidationRequest,
    TrustCheckRequest,
    UserLoginRequest,
    UserRegisterRequest,
)

router = APIRouter(prefix="/api/v1")

# ── Auth ──────────────────────────────────────────────────────────────────────

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post("/register")
async def register(data: UserRegisterRequest, db: DbSession):
    user, tokens = await AuthController(db).register(data)
    return APIResponse(data={"user": user, "tokens": tokens}, message="Registration successful")


@auth_router.post("/login")
async def login(data: UserLoginRequest, db: DbSession):
    user, tokens = await AuthController(db).login(data)
    return APIResponse(data={"user": user, "tokens": tokens}, message="Login successful")


@auth_router.post("/refresh")
async def refresh(data: RefreshTokenRequest, db: DbSession):
    tokens = await AuthController(db).refresh(data.refresh_token)
    return APIResponse(data=tokens, message="Token refreshed")


router.include_router(auth_router)

# ── Inbox ─────────────────────────────────────────────────────────────────────

inbox_router = APIRouter(prefix="/emails", tags=["Inbox"])


@inbox_router.get("")
async def list_emails(
    db: DbSession,
    current_user: CurrentUser,
    unread_only: bool = False,
    flagged_only: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    items, total = await InboxController(db).list_emails(unread_only, flagged_only, limit, offset)
    return APIResponse(data={"items": items, "total": total, "limit": limit, "offset": offset})


@inbox_router.post("/sync")
async def sync_emails(db: DbSession, current_user: CurrentUser):
    result = await InboxController(db).sync_emails()
    return APIResponse(data=result, message=result.message)


@inbox_router.post("/process")
async def process_emails(data: EmailProcessRequest, db: DbSession, current_user: CurrentUser):
    result = await InboxController(db).process_emails(data, current_user.id)
    return APIResponse(data=result, message=result.message)


@inbox_router.get("/{email_id}")
async def get_email(email_id: UUID, db: DbSession, current_user: CurrentUser):
    email = await InboxController(db).get_email(email_id)
    return APIResponse(data=email)


router.include_router(inbox_router)

# ── Trust ─────────────────────────────────────────────────────────────────────

trust_router = APIRouter(prefix="/trust", tags=["Trust Engine"])


@trust_router.post("/check")
async def trust_check(data: TrustCheckRequest, db: DbSession, current_user: CurrentUser):
    result = await TrustController(db).check(data)
    return APIResponse(data=result, confidence=result.confidence)


router.include_router(trust_router)

# ── Documents ─────────────────────────────────────────────────────────────────

doc_router = APIRouter(prefix="/documents", tags=["Documents"])


@doc_router.post("/upload")
async def upload_document(
    db: DbSession,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    email_id: UUID | None = None,
):
    result = await DocumentController(db).upload(file, email_id)
    return APIResponse(data=result, message="Document uploaded")


@doc_router.post("/extract")
async def extract_document(
    db: DbSession, current_user: CurrentUser, attachment_id: UUID = Query(...)
):
    result = await DocumentController(db).extract(attachment_id)
    return APIResponse(data=result, confidence=result.confidence)


@doc_router.post("/classify")
async def classify_document(
    db: DbSession, current_user: CurrentUser, attachment_id: UUID = Query(...)
):
    result = await DocumentController(db).classify(attachment_id)
    return APIResponse(data=result, confidence=result.confidence)


@doc_router.post("/normalize")
async def normalize_document(
    db: DbSession, current_user: CurrentUser, extraction_id: UUID = Query(...)
):
    result = await DocumentController(db).normalize(extraction_id)
    return APIResponse(data=result, confidence=result.confidence)


router.include_router(doc_router)

# ── Rules ─────────────────────────────────────────────────────────────────────

rules_router = APIRouter(prefix="/rules", tags=["Rule Engine"])


@rules_router.post("/validate")
async def validate_rules(data: RuleValidationRequest, db: DbSession, current_user: CurrentUser):
    result = await RuleController(db).validate(data)
    return APIResponse(data=result, confidence=result.confidence)


router.include_router(rules_router)

# ── ERP ───────────────────────────────────────────────────────────────────────

erp_router = APIRouter(prefix="/erp", tags=["ERP"])


@erp_router.post("/export")
async def export_erp(data: ERPExportRequest, db: DbSession, current_user: CurrentUser):
    result = await ERPController(db).export(data, current_user.id)
    return APIResponse(data=result, message="ERP export generated")


@erp_router.get("/download/{export_id}")
async def download_erp(export_id: UUID, db: DbSession, current_user: CurrentUser):
    from app.repositories.invoice_repository import ERPExportRepository
    from app.core.exceptions import NotFoundError

    repo = ERPExportRepository(db)
    export = await repo.get_by_id(export_id)
    if not export:
        raise NotFoundError("ERPExport", str(export_id))
    return FileResponse(export.file_path, filename=f"erp_export_{export_id}.xlsx")


router.include_router(erp_router)

# ── Invoice ───────────────────────────────────────────────────────────────────

invoice_router = APIRouter(prefix="/invoice", tags=["Invoice"])


@invoice_router.post("/create")
async def create_invoice(data: InvoiceCreateRequest, db: DbSession, current_user: CurrentUser):
    result = await InvoiceController(db).create(data)
    return APIResponse(data=result, confidence=result.confidence_score)


@invoice_router.get("")
async def list_invoices(
    db: DbSession,
    current_user: CurrentUser,
    status: str | None = None,
    search: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    result = await InvoiceController(db).list_invoices(status, search, limit, offset)
    return APIResponse(data=result)


@invoice_router.get("/{invoice_id}")
async def get_invoice(invoice_id: UUID, db: DbSession, current_user: CurrentUser):
    result = await InvoiceController(db).get_invoice(invoice_id)
    return APIResponse(data=result)


router.include_router(invoice_router)

# ── Approval ──────────────────────────────────────────────────────────────────

approval_router = APIRouter(prefix="/approvals", tags=["Approval"])


@approval_router.get("")
async def list_approvals(db: DbSession, current_user: CurrentUser, status: str | None = None):
    items = await ApprovalController(db).list_approvals(status)
    return APIResponse(data={"items": items, "total": len(items)})


@approval_router.post("/{approval_id}/approve")
async def approve_invoice(
    approval_id: UUID, data: ApprovalActionRequest, db: DbSession, current_user: CurrentUser
):
    result = await ApprovalController(db).approve(approval_id, current_user.id, data)
    return APIResponse(data=result, message=result.message)


@approval_router.post("/{approval_id}/reject")
async def reject_invoice(
    approval_id: UUID, data: ApprovalActionRequest, db: DbSession, current_user: CurrentUser
):
    result = await ApprovalController(db).reject(approval_id, current_user.id, data)
    return APIResponse(data=result, message=result.message)


@approval_router.post("/{approval_id}/request-review")
async def request_review(
    approval_id: UUID, data: ApprovalActionRequest, db: DbSession, current_user: CurrentUser
):
    result = await ApprovalController(db).request_review(approval_id, current_user.id, data)
    return APIResponse(data=result, message=result.message)


router.include_router(approval_router)

# ── Dispatch ──────────────────────────────────────────────────────────────────

dispatch_router = APIRouter(prefix="/dispatch", tags=["Dispatch"])


@dispatch_router.post("/email")
async def dispatch_email(data: DispatchEmailRequest, db: DbSession, current_user: CurrentUser):
    result = await DispatchController(db).send_email(data, current_user.id)
    return APIResponse(data=result, message=f"Dispatch {result.status}")


@dispatch_router.post("/send")
async def dispatch_send(data: DispatchEmailRequest, db: DbSession, current_user: CurrentUser):
    result = await DispatchController(db).send_email(data, current_user.id)
    return APIResponse(data=result, message=f"Dispatch {result.status}")


router.include_router(dispatch_router)

# ── Analytics ─────────────────────────────────────────────────────────────────

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/dashboard")
async def analytics_dashboard(db: DbSession, current_user: CurrentUser):
    result = await AnalyticsController(db).dashboard()
    return APIResponse(data=result)


@analytics_router.get("/monthly")
async def analytics_monthly(db: DbSession, current_user: CurrentUser):
    result = await AnalyticsController(db).monthly()
    return APIResponse(data=result)


@analytics_router.get("/roi")
async def analytics_roi(db: DbSession, current_user: CurrentUser):
    result = await AnalyticsController(db).roi()
    return APIResponse(data=result)


router.include_router(analytics_router)

# ── Copilot ───────────────────────────────────────────────────────────────────

copilot_router = APIRouter(prefix="/copilot", tags=["AI Copilot"])


@copilot_router.post("/chat")
async def copilot_chat(data: CopilotChatRequest, db: DbSession, current_user: CurrentUser):
    result = await CopilotController(db).chat(current_user.id, data)
    return APIResponse(data=result, confidence=result.confidence)


router.include_router(copilot_router)

# ── Clients ───────────────────────────────────────────────────────────────────

clients_router = APIRouter(prefix="/clients", tags=["Clients"])


@clients_router.get("")
async def list_clients(db: DbSession, current_user: CurrentUser):
    from app.repositories.misc_repository import ClientRepository, VendorProfileRepository
    from app.repositories.invoice_repository import InvoiceRepository
    from sqlalchemy import func, select
    from app.models.invoice import Invoice

    client_repo = ClientRepository(db)
    clients = await client_repo.list_with_profiles()
    items = []
    for c in clients:
        result = await db.execute(
            select(func.count(), func.coalesce(func.sum(Invoice.total_amount), 0))
            .where(Invoice.client_id == c.id)
        )
        count, spend = result.one()
        trust = c.vendor_profile.reputation_score if c.vendor_profile else None
        risk = c.vendor_profile.risk_level if c.vendor_profile else "medium"
        items.append({
            "id": c.id,
            "name": c.name,
            "domain": c.domain,
            "email": c.email,
            "phone": c.phone,
            "city": c.city,
            "country": c.country,
            "is_active": c.is_active,
            "trust_score": trust,
            "invoice_count": count,
            "spend_ytd": float(spend or 0),
            "risk_level": risk,
        })
    return APIResponse(data={"items": items, "total": len(items)})


router.include_router(clients_router)

# ── Agents ────────────────────────────────────────────────────────────────────

agents_router = APIRouter(prefix="/agents", tags=["Agents"])


@agents_router.get("/status")
async def agent_status(db: DbSession, current_user: CurrentUser):
    from sqlalchemy import select
    from app.models.audit import AgentRunLog

    result = await db.execute(
        select(AgentRunLog).order_by(AgentRunLog.created_at.desc()).limit(50)
    )
    logs = list(result.scalars().all())

    agent_names = [
        "Mail Intelligence", "Trust Verification", "Document Understanding",
        "OCR Extraction", "Business Rules", "Invoice Generation",
        "ERP Integration", "Analytics",
    ]
    agents = []
    for name in agent_names:
        agent_logs = [l for l in logs if l.agent_name == name]
        latest = agent_logs[0] if agent_logs else None
        agents.append({
            "name": name,
            "status": latest.status if latest else "idle",
            "task": latest.task_description if latest else "Standby",
            "time": f"{latest.duration_ms}ms" if latest and latest.duration_ms else "—",
            "conf": latest.confidence if latest and latest.confidence else 100,
        })

    live_logs = [
        {
            "time": l.created_at.strftime("%H:%M:%S"),
            "level": l.log_level,
            "message": l.message,
        }
        for l in logs[:20]
    ]

    return APIResponse(data={
        "agents": agents,
        "pipeline_running": any(a["status"] in ("active", "thinking") for a in agents),
        "live_logs": live_logs,
    })


router.include_router(agents_router)

# ── Notifications ─────────────────────────────────────────────────────────────

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get("")
async def list_notifications(db: DbSession, current_user: CurrentUser):
    from app.services.notification_service import NotificationService
    service = NotificationService(db)
    items = await service.list_unread(current_user.id)
    return APIResponse(data={"items": items, "total": len(items)})


router.include_router(notifications_router)

# ── Exceptions ────────────────────────────────────────────────────────────────

exceptions_router = APIRouter(prefix="/exceptions", tags=["Exceptions"])


@exceptions_router.get("")
async def list_exceptions(db: DbSession, current_user: CurrentUser):
    from app.services.approval_service import ApprovalService

    service = ApprovalService(db)
    all_items = await service.list_queue_dicts()
    columns = {
        "needs_review": [],
        "waiting_approval": [],
        "rejected": [],
        "resolved": [],
    }
    for item in all_items:
        status = item.get("status", "needs_review")
        key = status if status in columns else "needs_review"
        columns[key].append(item)
    return APIResponse(data={"columns": columns})


router.include_router(exceptions_router)

# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health():
    return APIResponse(data={"status": "healthy", "service": "aurora-tia-backend"})
