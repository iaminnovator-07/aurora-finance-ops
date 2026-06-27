"""Email intelligence: summary, intent, priority, spam detection."""

import re
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.base import EmailIntent, EmailPriority
from app.repositories.email_repository import EmailRepository
from app.services.ai.gemini_service import GeminiService


class MailIntelligenceService:
    SPAM_KEYWORDS = [
        "lottery", "winner", "crypto", "bitcoin", "wire transfer",
        "urgent action", "click here", "unsubscribe", "viagra",
        "nigerian prince", "free money", "act now",
    ]
    INVOICE_KEYWORDS = ["invoice", "payment due", "bill", "remittance", "payable"]
    TIMESHEET_KEYWORDS = ["timesheet", "hours worked", "hourly", "payroll", "overtime"]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.email_repo = EmailRepository(session)
        self.gemini = GeminiService(session)

    async def analyze_email(self, email_id: UUID) -> dict:
        email = await self.email_repo.get_by_id(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        summary = await self.generate_summary(email_id)
        intent = await self.detect_intent(email_id)
        priority = await self.detect_priority(email_id)
        spam = await self.detect_spam(email_id)

        email.ai_summary = summary["text"]
        email.intent = intent["intent"]
        email.priority = priority["priority"]
        email.is_spam = spam["is_spam"]
        await self.email_repo.update(email)

        return {
            "email_id": str(email_id),
            "summary": summary,
            "intent": intent,
            "priority": priority,
            "spam": spam,
            "confidence": round(
                (summary["confidence"] + intent["confidence"] + priority["confidence"] + spam["confidence"]) / 4,
                2,
            ),
        }

    async def generate_summary(self, email_id: UUID) -> dict:
        email = await self.email_repo.get_by_id(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        body = (email.body_text or "")[:4000]
        prompt = (
            f"Summarize this email in 2-3 sentences.\n"
            f"From: {email.from_email}\nSubject: {email.subject}\n\n{body}"
        )
        result = await self.gemini.generate_text(prompt, system_instruction="You summarize business emails concisely.")
        return {"text": result["text"], "confidence": result["confidence"]}

    async def detect_intent(self, email_id: UUID) -> dict:
        email = await self.email_repo.get_by_id(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        combined = f"{email.subject} {email.body_text or ''}".lower()

        heuristic_intent = EmailIntent.UNKNOWN.value
        confidence = 0.55
        if any(kw in combined for kw in self.INVOICE_KEYWORDS):
            heuristic_intent = EmailIntent.INVOICE_SUBMISSION.value
            confidence = 0.75
        elif any(kw in combined for kw in self.TIMESHEET_KEYWORDS):
            heuristic_intent = EmailIntent.TIMESHEET.value
            confidence = 0.78
        elif any(kw in combined for kw in self.SPAM_KEYWORDS):
            heuristic_intent = EmailIntent.SPAM.value
            confidence = 0.8

        prompt = (
            f"Classify email intent as one of: invoice_submission, timesheet, receipt, inquiry, spam, unknown.\n"
            f"Subject: {email.subject}\nBody: {(email.body_text or '')[:2000]}"
        )
        ai_result = await self.gemini.generate_text(prompt)
        ai_intent = ai_result["text"].strip().lower().replace(" ", "_")
        valid = {e.value for e in EmailIntent}
        if ai_intent in valid:
            return {"intent": ai_intent, "confidence": ai_result["confidence"]}
        return {"intent": heuristic_intent, "confidence": confidence}

    async def detect_priority(self, email_id: UUID) -> dict:
        email = await self.email_repo.get_by_id(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        combined = f"{email.subject} {email.body_text or ''}".lower()
        priority = EmailPriority.MEDIUM.value
        confidence = 0.7

        if any(w in combined for w in ("urgent", "asap", "immediate", "critical", "overdue")):
            priority = EmailPriority.CRITICAL.value
            confidence = 0.88
        elif any(w in combined for w in ("invoice", "payment", "due", "approval")):
            priority = EmailPriority.HIGH.value
            confidence = 0.82
        elif any(w in combined for w in ("fyi", "newsletter", "update", "reminder")):
            priority = EmailPriority.LOW.value
            confidence = 0.75

        if email.is_flagged:
            priority = EmailPriority.HIGH.value
            confidence = max(confidence, 0.85)

        return {"priority": priority, "confidence": confidence}

    async def detect_spam(self, email_id: UUID) -> dict:
        email = await self.email_repo.get_by_id(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        combined = f"{email.subject} {email.body_text or ''}".lower()
        score = 0
        matched: list[str] = []

        for kw in self.SPAM_KEYWORDS:
            if kw in combined:
                score += 15
                matched.append(kw)

        if re.search(r"http[s]?://[^\s]{50,}", combined):
            score += 10
            matched.append("long_urls")

        suspicious_domains = {"mail.ru", "tempmail", "guerrillamail"}
        domain = email.from_email.split("@")[-1].lower() if "@" in email.from_email else ""
        if domain in suspicious_domains:
            score += 25
            matched.append(f"suspicious_domain:{domain}")

        is_spam = score >= 30
        confidence = min(95.0, 50.0 + score)

        return {
            "is_spam": is_spam,
            "spam_score": score,
            "matched_signals": matched,
            "confidence": confidence,
            "reason": f"Spam score {score} based on {len(matched)} signal(s)" if matched else "No spam signals detected",
        }
