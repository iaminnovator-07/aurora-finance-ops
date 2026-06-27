"""AI copilot chat with database context."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.audit import AIConversation
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.misc_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.services.ai.gemini_service import GeminiService


class CopilotService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.gemini = GeminiService(session)
        self.user_repo = UserRepository(session)
        self.invoice_repo = InvoiceRepository(session)
        self.audit_repo = AuditLogRepository(session)

    async def chat(
        self,
        user_id: UUID,
        message: str,
        conversation_id: UUID | None = None,
    ) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", str(user_id))

        conversation = await self._get_or_create_conversation(user_id, conversation_id)
        context = await self._build_context(user_id)

        system_prompt = (
            "You are Aurora TIA copilot, an AI assistant for invoice processing and email trust analysis. "
            "Use the provided database context to answer questions accurately. "
            "Always include a confidence estimate in your reasoning."
        )
        context_block = self._format_context(context)
        full_prompt = (
            f"Context from Aurora TIA database:\n{context_block}\n\n"
            f"User question: {message}\n\n"
            "Provide a helpful, concise answer based on the context."
        )

        ai_response = await self.gemini.generate_text(full_prompt, system_instruction=system_prompt)

        messages = list(conversation.messages or [])
        messages.append({"role": "user", "content": message, "timestamp": datetime.now(UTC).isoformat()})
        messages.append(
            {
                "role": "assistant",
                "content": ai_response["text"],
                "confidence": ai_response["confidence"],
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        conversation.messages = messages
        conversation.context_data = context
        conversation.title = conversation.title or message[:80]
        await self.session.flush()
        await self.session.refresh(conversation)

        return {
            "conversation_id": str(conversation.id),
            "reply": ai_response["text"],
            "confidence": ai_response["confidence"],
            "context_summary": {
                "recent_invoices": len(context.get("recent_invoices", [])),
                "recent_audit_logs": len(context.get("recent_audit_logs", [])),
            },
        }

    async def _get_or_create_conversation(
        self, user_id: UUID, conversation_id: UUID | None
    ) -> AIConversation:
        if conversation_id:
            conversation = await self.session.get(AIConversation, conversation_id)
            if not conversation or conversation.user_id != user_id:
                raise NotFoundError("AIConversation", str(conversation_id))
            return conversation

        conversation = AIConversation(user_id=user_id, messages=[], is_active=True)
        self.session.add(conversation)
        await self.session.flush()
        await self.session.refresh(conversation)
        return conversation

    async def _build_context(self, user_id: UUID) -> dict:
        invoices, _ = await self.invoice_repo.list_invoices(limit=10)
        audit_logs = await self.audit_repo.list_by_entity("user", str(user_id))

        result = await self.session.execute(
            select(AIConversation)
            .where(AIConversation.user_id == user_id, AIConversation.is_active.is_(True))
            .limit(3)
        )
        prior_conversations = list(result.scalars().all())

        return {
            "recent_invoices": [
                {
                    "invoice_number": inv.invoice_number,
                    "status": inv.status,
                    "vendor": inv.vendor_name,
                    "total": str(inv.total_amount) if inv.total_amount else None,
                    "confidence": inv.confidence_score,
                }
                for inv in invoices
            ],
            "recent_audit_logs": [
                {
                    "action": log.action,
                    "module": log.module,
                    "entity_type": log.entity_type,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in audit_logs[:10]
            ],
            "prior_conversation_count": len(prior_conversations),
        }

    @staticmethod
    def _format_context(context: dict) -> str:
        lines = []
        for inv in context.get("recent_invoices", []):
            lines.append(
                f"- Invoice {inv['invoice_number']}: {inv['status']}, vendor={inv['vendor']}, "
                f"total={inv['total']}, confidence={inv['confidence']}"
            )
        for log in context.get("recent_audit_logs", []):
            lines.append(f"- Audit: {log['action']} in {log['module']} ({log['entity_type']})")
        if not lines:
            return "No recent invoice or audit data available."
        return "\n".join(lines)
