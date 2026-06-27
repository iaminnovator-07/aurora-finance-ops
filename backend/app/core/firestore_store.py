"""Firestore document store — async wrapper around firebase-admin."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.firebase import get_firestore

logger = logging.getLogger(__name__)


def _serialize(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if hasattr(value, "__float__") and type(value).__name__ in ("Decimal",):
        return float(value)
    return value


def _doc_to_dict(doc) -> dict | None:
    if not doc.exists:
        return None
    data = doc.to_dict()
    data["id"] = doc.id
    return data


class FirestoreStore:
    """Generic Firestore CRUD used when DATABASE_BACKEND=firestore."""

    def __init__(self, collection: str):
        self.collection = collection
        self._db = get_firestore()

    def _col(self):
        if not self._db:
            raise RuntimeError("Firestore not initialized — set FIREBASE credentials or use DATABASE_BACKEND=postgresql")
        return self._db.collection(self.collection)

    async def _run(self, fn):
        return await asyncio.get_event_loop().run_in_executor(None, fn)

    async def get(self, doc_id: str) -> dict | None:
        def _get():
            return _doc_to_dict(self._col().document(doc_id).get())
        return await self._run(_get)

    async def create(self, data: dict, doc_id: str | None = None) -> dict:
        doc_id = doc_id or str(uuid4())
        payload = _serialize({**data, "created_at": datetime.now(UTC).isoformat(), "updated_at": datetime.now(UTC).isoformat()})

        def _create():
            self._col().document(doc_id).set(payload)
            return {"id": doc_id, **payload}

        return await self._run(_create)

    async def update(self, doc_id: str, data: dict) -> dict:
        payload = _serialize({**data, "updated_at": datetime.now(UTC).isoformat()})

        def _update():
            ref = self._col().document(doc_id)
            ref.update(payload)
            return _doc_to_dict(ref.get())

        return await self._run(_update)

    async def delete(self, doc_id: str) -> None:
        def _delete():
            self._col().document(doc_id).delete()
        await self._run(_delete)

    async def list(self, limit: int = 100, order_by: str | None = "created_at") -> list[dict]:
        def _list():
            q = self._col()
            if order_by:
                try:
                    q = q.order_by(order_by, direction="DESCENDING")
                except Exception:
                    pass
            return [_doc_to_dict(d) for d in q.limit(limit).stream()]

        return await self._run(_list)

    async def query(self, field: str, op: str, value: Any, limit: int = 50) -> list[dict]:
        def _query():
            return [_doc_to_dict(d) for d in self._col().where(field, op, value).limit(limit).stream()]

        return await self._run(_query)

    async def count(self) -> int:
        docs = await self.list(limit=10000)
        return len(docs)


# Collection singletons
COLLECTIONS = {
    "users": "users",
    "clients": "clients",
    "client_contacts": "client_contacts",
    "emails": "emails",
    "email_attachments": "email_attachments",
    "document_extractions": "document_extractions",
    "trust_scores": "trust_scores",
    "vendor_profiles": "vendor_profiles",
    "invoices": "invoices",
    "erp_exports": "erp_exports",
    "approval_queue": "approval_queue",
    "rule_engine_logs": "rule_engine_logs",
    "business_rules": "business_rules",
    "audit_logs": "audit_logs",
    "notifications": "notifications",
    "analytics_snapshots": "analytics_snapshots",
    "ai_conversations": "ai_conversations",
    "dispatch_records": "dispatch_records",
    "agent_run_logs": "agent_run_logs",
}


def store(name: str) -> FirestoreStore:
    return FirestoreStore(COLLECTIONS.get(name, name))
