"""Mirror SQLAlchemy writes to Firestore for Firebase-backed deployments."""

import logging
from typing import Any

from app.config import get_settings
from app.core.firestore_store import store

logger = logging.getLogger(__name__)

# Map SQLAlchemy model class names to Firestore collections
MODEL_COLLECTION_MAP = {
    "User": "users",
    "Client": "clients",
    "ClientContact": "client_contacts",
    "Email": "emails",
    "EmailAttachment": "email_attachments",
    "DocumentExtraction": "document_extractions",
    "TrustScore": "trust_scores",
    "VendorProfile": "vendor_profiles",
    "Invoice": "invoices",
    "ERPExport": "erp_exports",
    "ApprovalQueue": "approval_queue",
    "RuleEngineLog": "rule_engine_logs",
    "BusinessRule": "business_rules",
    "AuditLog": "audit_logs",
    "Notification": "notifications",
    "AnalyticsSnapshot": "analytics_snapshots",
    "AIConversation": "ai_conversations",
    "DispatchRecord": "dispatch_records",
    "AgentRunLog": "agent_run_logs",
}


def _model_to_dict(entity: Any) -> dict:
    data: dict = {}
    for col in entity.__table__.columns:
        val = getattr(entity, col.name, None)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        elif hasattr(val, "__str__") and type(val).__name__ == "UUID":
            val = str(val)
        elif hasattr(val, "__float__") and type(val).__name__ == "Decimal":
            val = float(val)
        data[col.name] = val
    if hasattr(entity, "id") and entity.id:
        data["id"] = str(entity.id)
    return data


async def sync_entity_to_firestore(entity: Any, operation: str = "upsert") -> None:
    """Dual-write entity to Firestore when firebase sync is enabled."""
    settings = get_settings()
    if settings.database_backend not in ("firestore", "postgresql"):
        return

    # Always sync when firestore backend OR when explicitly using dual-write mode
    if settings.database_backend == "postgresql" and not settings.firebase_project_id:
        return

    collection = MODEL_COLLECTION_MAP.get(entity.__class__.__name__)
    if not collection:
        return

    try:
        fs = store(collection)
        data = _model_to_dict(entity)
        doc_id = data.pop("id", None) or str(getattr(entity, "id", ""))
        if not doc_id:
            return
        if operation == "delete":
            await fs.delete(doc_id)
        elif operation == "create":
            await fs.create(data, doc_id=doc_id)
        else:
            existing = await fs.get(doc_id)
            if existing:
                await fs.update(doc_id, data)
            else:
                await fs.create(data, doc_id=doc_id)
    except Exception as exc:
        logger.warning("Firestore sync failed for %s: %s", entity.__class__.__name__, exc)
