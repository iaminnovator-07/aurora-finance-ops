"""Email trust scoring with DNS authentication checks."""

import logging
import re
from datetime import UTC, datetime
from uuid import UUID

import dns.resolver
from rapidfuzz import fuzz
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import NotFoundError, ProcessingError
from app.models.document import TrustScore
from app.repositories.email_repository import EmailRepository
from app.repositories.misc_repository import (
    ClientRepository,
    TrustScoreRepository,
    VendorProfileRepository,
)

logger = logging.getLogger(__name__)


class TrustEngineService:
    WEIGHTS = {
        "identity": 0.25,
        "content": 0.20,
        "domain": 0.20,
        "vendor": 0.20,
        "duplicate": 0.15,
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.email_repo = EmailRepository(session)
        self.trust_repo = TrustScoreRepository(session)
        self.client_repo = ClientRepository(session)
        self.vendor_repo = VendorProfileRepository(session)

    async def check_email(self, email_id: UUID) -> TrustScore:
        email = await self.email_repo.get_with_details(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        timeline: list[dict] = []
        checks: dict = {}

        def add_step(step: str, score: float, detail: str) -> None:
            timeline.append(
                {
                    "step": step,
                    "score": round(score, 2),
                    "detail": detail,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )

        domain = email.from_email.split("@")[-1] if "@" in email.from_email else ""
        spf_result, dkim_result, dmarc_result = self._check_email_auth(domain)
        checks["spf"] = spf_result
        checks["dkim"] = dkim_result
        checks["dmarc"] = dmarc_result

        identity_score = self._score_identity(email, spf_result, dkim_result, dmarc_result)
        add_step(
            "identity",
            identity_score,
            f"SPF={spf_result}, DKIM={dkim_result}, DMARC={dmarc_result}",
        )

        content_score = self._score_content(email)
        add_step("content", content_score, "Body/subject phishing and anomaly heuristics")

        domain_trust = await self._score_domain(domain, email.client_id)
        add_step("domain_trust", domain_trust, f"Domain reputation for {domain}")

        vendor_reputation = await self._score_vendor(email.client_id)
        add_step("vendor_reputation", vendor_reputation, "Historical vendor profile score")

        duplicate_score = await self._score_duplicates(email)
        add_step("duplicate", duplicate_score, "Subject/sender duplicate similarity")

        overall = (
            identity_score * self.WEIGHTS["identity"]
            + content_score * self.WEIGHTS["content"]
            + domain_trust * self.WEIGHTS["domain"]
            + vendor_reputation * self.WEIGHTS["vendor"]
            + duplicate_score * self.WEIGHTS["duplicate"]
        )
        overall = round(overall, 2)

        if overall >= self.settings.trust_auto_approve_threshold:
            risk_level = "low"
        elif overall >= self.settings.manual_review_trust_threshold:
            risk_level = "medium"
        else:
            risk_level = "high"

        reason = (
            f"Overall trust {overall}: identity={identity_score}, content={content_score}, "
            f"domain={domain_trust}, vendor={vendor_reputation}, duplicate={duplicate_score}"
        )

        existing = await self.trust_repo.get_by_email_id(email_id)
        if existing:
            existing.identity_score = identity_score
            existing.content_score = content_score
            existing.domain_trust_score = domain_trust
            existing.vendor_reputation_score = vendor_reputation
            existing.duplicate_score = duplicate_score
            existing.overall_score = overall
            existing.risk_level = risk_level
            existing.reason = reason
            existing.checks = checks
            existing.reasoning_timeline = timeline
            existing.spf_result = spf_result
            existing.dkim_result = dkim_result
            existing.dmarc_result = dmarc_result
            existing.client_id = email.client_id
            trust_score = await self.trust_repo.update(existing)
        else:
            trust_score = TrustScore(
                email_id=email_id,
                client_id=email.client_id,
                identity_score=identity_score,
                content_score=content_score,
                domain_trust_score=domain_trust,
                vendor_reputation_score=vendor_reputation,
                duplicate_score=duplicate_score,
                overall_score=overall,
                risk_level=risk_level,
                reason=reason,
                checks=checks,
                reasoning_timeline=timeline,
                spf_result=spf_result,
                dkim_result=dkim_result,
                dmarc_result=dmarc_result,
            )
            trust_score = await self.trust_repo.create(trust_score)

        email.trust_score_id = trust_score.id
        await self.email_repo.update(email)
        return trust_score

    async def check_adhoc(self, from_email: str, subject: str, body: str) -> dict:
        """Run trust scoring without a persisted email record."""
        from types import SimpleNamespace

        domain = from_email.split("@")[-1] if "@" in from_email else ""
        fake_email = SimpleNamespace(
            id=None,
            from_email=from_email,
            from_name=from_email.split("@")[0],
            subject=subject,
            body_text=body,
            client_id=None,
        )
        spf_result, dkim_result, dmarc_result = self._check_email_auth(domain)
        checks = {"spf": spf_result, "dkim": dkim_result, "dmarc": dmarc_result}
        timeline: list[dict] = []

        identity_score = self._score_identity(fake_email, spf_result, dkim_result, dmarc_result)
        timeline.append({"step": "identity", "score": identity_score, "detail": checks})
        content_score = self._score_content(fake_email)
        timeline.append({"step": "content", "score": content_score, "detail": "Content heuristics"})
        domain_trust = await self._score_domain(domain, None)
        timeline.append({"step": "domain_trust", "score": domain_trust, "detail": domain})
        vendor_reputation = 50.0
        duplicate_score = 100.0

        overall = round(
            identity_score * self.WEIGHTS["identity"]
            + content_score * self.WEIGHTS["content"]
            + domain_trust * self.WEIGHTS["domain"]
            + vendor_reputation * self.WEIGHTS["vendor"]
            + duplicate_score * self.WEIGHTS["duplicate"],
            2,
        )
        risk_level = (
            "low" if overall >= self.settings.trust_auto_approve_threshold
            else "medium" if overall >= self.settings.manual_review_trust_threshold
            else "high"
        )
        return self._to_response(
            overall, identity_score, content_score, domain_trust,
            vendor_reputation, duplicate_score, risk_level, checks, timeline,
        )

    def _to_response(
        self, overall, identity, content, domain, vendor, duplicate,
        risk_level, checks, timeline,
    ) -> dict:
        return {
            "trust_score": overall,
            "identity_score": identity,
            "content_score": content,
            "domain_trust_score": domain,
            "vendor_reputation_score": vendor,
            "duplicate_score": duplicate,
            "overall_score": overall,
            "risk_level": risk_level,
            "reason": (
                f"Overall trust {overall}: identity={identity}, content={content}, "
                f"domain={domain}, vendor={vendor}, duplicate={duplicate}"
            ),
            "checks": checks,
            "reasoning_timeline": timeline,
            "confidence": round(min(overall, 99.0), 2),
        }

    async def check_email_dict(self, email_id: UUID) -> dict:
        ts = await self.check_email(email_id)
        return self._to_response(
            ts.overall_score, ts.identity_score, ts.content_score,
            ts.domain_trust_score, ts.vendor_reputation_score, ts.duplicate_score,
            ts.risk_level, ts.checks, ts.reasoning_timeline,
        )

    def _check_email_auth(self, domain: str) -> tuple[str, str, str]:
        if not domain:
            return "fail", "fail", "fail"

        spf = self._check_spf(domain)
        dkim = self._check_dkim(domain)
        dmarc = self._check_dmarc(domain)
        return spf, dkim, dmarc

    def _check_spf(self, domain: str) -> str:
        try:
            answers = dns.resolver.resolve(domain, "TXT")
            for rdata in answers:
                txt = str(rdata).strip('"')
                if txt.lower().startswith("v=spf1"):
                    if " -all" in txt.lower():
                        return "pass_strict"
                    if "~all" in txt.lower() or "?all" in txt.lower():
                        return "pass_soft"
                    return "pass"
            return "none"
        except Exception as exc:
            logger.debug("SPF check failed for %s: %s", domain, exc)
            return "unknown"

    def _check_dkim(self, domain: str) -> str:
        selectors = ["default", "google", "selector1", "selector2", "k1"]
        for selector in selectors:
            dkim_domain = f"{selector}._domainkey.{domain}"
            try:
                answers = dns.resolver.resolve(dkim_domain, "TXT")
                for rdata in answers:
                    txt = str(rdata).strip('"')
                    if "v=dkim1" in txt.lower() or "p=" in txt.lower():
                        return "pass"
            except Exception:
                continue
        return "none"

    def _check_dmarc(self, domain: str) -> str:
        try:
            answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
            for rdata in answers:
                txt = str(rdata).strip('"').lower()
                if txt.startswith("v=dmarc1"):
                    if "p=reject" in txt:
                        return "pass_strict"
                    if "p=quarantine" in txt:
                        return "pass_quarantine"
                    return "pass"
            return "none"
        except Exception as exc:
            logger.debug("DMARC check failed for %s: %s", domain, exc)
            return "unknown"

    def _score_identity(
        self, email, spf: str, dkim: str, dmarc: str
    ) -> float:
        score = 50.0
        spf_scores = {"pass_strict": 25, "pass_soft": 20, "pass": 18, "none": 5, "unknown": 8, "fail": -20}
        dkim_scores = {"pass": 15, "none": 0, "unknown": 3, "fail": -15}
        dmarc_scores = {"pass_strict": 15, "pass_quarantine": 12, "pass": 10, "none": 0, "unknown": 3, "fail": -15}
        score += spf_scores.get(spf, 0)
        score += dkim_scores.get(dkim, 0)
        score += dmarc_scores.get(dmarc, 0)

        if email.from_name and email.from_email:
            local = email.from_email.split("@")[0].replace(".", " ").replace("_", " ")
            if fuzz.partial_ratio(email.from_name.lower(), local.lower()) > 60:
                score += 5
        return max(0.0, min(100.0, score))

    def _score_content(self, email) -> float:
        score = 70.0
        subject = (email.subject or "").lower()
        body = (email.body_text or "").lower()
        combined = f"{subject} {body}"

        spam_signals = [
            r"urgent action required",
            r"wire transfer",
            r"bank account change",
            r"click here immediately",
            r"lottery winner",
            r"crypto investment",
        ]
        for pat in spam_signals:
            if re.search(pat, combined):
                score -= 15

        if "invoice" in combined or "timesheet" in combined:
            score += 10
        if len(body) < 20:
            score -= 5
        return max(0.0, min(100.0, score))

    async def _score_domain(self, domain: str, client_id: UUID | None) -> float:
        if not domain:
            return 30.0
        client = await self.client_repo.get_by_domain(domain)
        if client:
            return 90.0
        if client_id:
            linked = await self.client_repo.get_by_id(client_id)
            if linked and linked.domain == domain:
                return 85.0
        free_providers = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}
        if domain.lower() in free_providers:
            return 45.0
        return 65.0

    async def _score_vendor(self, client_id: UUID | None) -> float:
        if not client_id:
            return 50.0
        profile = await self.vendor_repo.get_by_client_id(client_id)
        if not profile:
            return 55.0
        base = profile.reputation_score
        if profile.fraud_incidents > 0:
            base -= profile.fraud_incidents * 10
        if profile.is_verified:
            base += 10
        return max(0.0, min(100.0, base))

    async def _score_duplicates(self, email) -> float:
        duplicates = await self.email_repo.find_duplicates(email.subject, email.from_email)
        others = [d for d in duplicates if d.id != email.id]
        if not others:
            return 100.0
        best = max(
            fuzz.ratio(email.subject, d.subject) for d in others
        )
        if best >= 95:
            return 20.0
        if best >= 80:
            return 50.0
        return 85.0
