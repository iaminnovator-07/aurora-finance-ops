"""Business rule validation engine for invoices."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import NotFoundError
from app.models.approval import RuleEngineLog
from app.models.base import RuleSeverity
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.misc_repository import (
    BusinessRuleRepository,
    ClientRepository,
    RuleEngineLogRepository,
)


class RuleEngineService:
    SALARY_HOURLY_CAP = Decimal("500.00")
    MAX_WEEKLY_HOURS = Decimal("80.00")

    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = get_settings()
        self.invoice_repo = InvoiceRepository(session)
        self.rule_log_repo = RuleEngineLogRepository(session)
        self.business_rule_repo = BusinessRuleRepository(session)
        self.client_repo = ClientRepository(session)

    async def validate_invoice(self, invoice_id: UUID) -> dict[str, Any]:
        invoice = await self.invoice_repo.get_with_details(invoice_id)
        if not invoice:
            raise NotFoundError("Invoice", str(invoice_id))

        rules = [
            self._check_duplicate,
            self._check_budget,
            self._check_missing_fields,
            self._check_currency,
            self._check_invoice_number,
            self._check_vendor,
            self._check_working_hours,
            self._check_tax,
            self._check_po,
            self._check_salary_limits,
            self._check_client_rules,
        ]

        results: list[dict[str, Any]] = []
        for check in rules:
            result = await check(invoice)
            results.append(result)
            await self._persist_log(invoice_id, result)

        failed = [r for r in results if not r["passed"]]
        critical_failed = [r for r in failed if r["severity"] in ("high", "critical")]

        summary = {
            "invoice_id": str(invoice_id),
            "passed": len(failed) == 0,
            "total_rules": len(results),
            "passed_count": len(results) - len(failed),
            "failed_count": len(failed),
            "critical_failures": len(critical_failed),
            "rules": results,
            "confidence": round(
                sum(r.get("confidence", 80) for r in results) / max(len(results), 1), 2
            ),
        }

        invoice.rules_passed = summary["passed"]
        invoice.rules_summary = summary
        await self.invoice_repo.update(invoice)
        return self._format_response(summary)

    async def validate_email(self, email_id: UUID) -> dict[str, Any]:
        from app.repositories.email_repository import EmailRepository

        email_repo = EmailRepository(self.session)
        email = await email_repo.get_with_details(email_id)
        if not email:
            raise NotFoundError("Email", str(email_id))

        items, _ = await self.invoice_repo.list_invoices(limit=100, offset=0)
        for inv in items:
            if inv.email_id == email_id:
                return await self.validate_invoice(inv.id)

        return await self.validate_data({
            "from_email": email.from_email,
            "subject": email.subject,
            "body": email.body_text,
        })

    async def validate_data(self, data: dict[str, Any]) -> dict[str, Any]:
        results = []
        checks = [
            ("duplicate_check", "duplicate", self._check_data_duplicate),
            ("missing_fields", "validation", self._check_data_missing),
            ("spam_signals", "fraud", self._check_data_spam),
        ]
        for name, category, fn in checks:
            result = fn(data)
            result["rule_name"] = name
            result["category"] = category
            results.append(result)
        failed = [r for r in results if not r["passed"]]
        summary = {
            "passed": len(failed) == 0,
            "total_rules": len(results),
            "passed_count": len(results) - len(failed),
            "failed_count": len(failed),
            "rules": results,
            "confidence": round(sum(r.get("confidence", 80) for r in results) / len(results), 2),
        }
        return self._format_response(summary)

    def _format_response(self, summary: dict[str, Any]) -> dict[str, Any]:
        results = []
        for r in summary.get("rules", []):
            results.append({
                "rule_name": r.get("rule_name", r.get("name", "unknown")),
                "category": r.get("category", "general"),
                "passed": r["passed"],
                "severity": r.get("severity", "info"),
                "reason": r.get("reason", ""),
                "suggestion": r.get("suggestion"),
                "confidence": r.get("confidence", 80.0),
            })
        return {
            "passed": summary["passed"],
            "total_rules": summary["total_rules"],
            "passed_count": summary["passed_count"],
            "failed_count": summary["failed_count"],
            "results": results,
            "confidence": summary.get("confidence", 80.0),
        }

    def _check_data_duplicate(self, data: dict) -> dict:
        return {"passed": True, "severity": "info", "reason": "No duplicate context without invoice", "confidence": 70.0}

    def _check_data_missing(self, data: dict) -> dict:
        missing = [k for k in ("from_email", "subject") if not data.get(k)]
        passed = len(missing) == 0
        return {
            "passed": passed,
            "severity": "medium" if not passed else "info",
            "reason": f"Missing fields: {missing}" if missing else "Required fields present",
            "suggestion": "Provide sender email and subject" if missing else None,
            "confidence": 95.0,
        }

    def _check_data_spam(self, data: dict) -> dict:
        from app.utils.email_utils import detect_spam_signals
        is_spam, signals = detect_spam_signals(
            data.get("subject", ""), data.get("body", ""), data.get("from_email", "")
        )
        return {
            "passed": not is_spam,
            "severity": "critical" if is_spam else "info",
            "reason": f"Spam signals: {signals}" if is_spam else "No spam signals detected",
            "suggestion": "Reject and report to security" if is_spam else None,
            "confidence": 88.0,
        }

    async def _persist_log(self, invoice_id: UUID, result: dict[str, Any]) -> RuleEngineLog:
        log = RuleEngineLog(
            invoice_id=invoice_id,
            rule_name=result["rule_name"],
            rule_category=result["category"],
            passed=result["passed"],
            severity=result["severity"],
            reason=result["reason"],
            suggestion=result.get("suggestion"),
            input_data=result.get("input_data"),
            output_data={"passed": result["passed"]},
            confidence=result.get("confidence"),
        )
        return await self.rule_log_repo.create(log)

    async def _check_duplicate(self, invoice) -> dict[str, Any]:
        similar = await self.invoice_repo.find_similar_invoices(
            invoice.vendor_name, invoice.total_amount
        )
        dupes = [i for i in similar if i.id != invoice.id and i.invoice_number != invoice.invoice_number]
        passed = len(dupes) == 0
        return {
            "rule_name": "duplicate_detection",
            "category": "fraud",
            "passed": passed,
            "reason": "No duplicate invoices found" if passed else f"Found {len(dupes)} similar invoice(s)",
            "suggestion": None if passed else "Verify this is not a resubmission of an existing invoice",
            "severity": RuleSeverity.HIGH.value if not passed else RuleSeverity.INFO.value,
            "confidence": 92.0 if passed else 85.0,
            "input_data": {"vendor": invoice.vendor_name, "amount": str(invoice.total_amount)},
        }

    async def _check_budget(self, invoice) -> dict[str, Any]:
        if not invoice.client_id or not invoice.total_amount:
            return self._skip_rule("budget_limit", "budget", "No client or amount to validate")
        client = await self.client_repo.get_by_id(invoice.client_id)
        if not client or not client.budget_limit:
            return self._skip_rule("budget_limit", "budget", "Client has no budget limit configured")
        passed = invoice.total_amount <= client.budget_limit
        return {
            "rule_name": "budget_limit",
            "category": "budget",
            "passed": passed,
            "reason": (
                f"Amount {invoice.total_amount} within budget {client.budget_limit}"
                if passed
                else f"Amount {invoice.total_amount} exceeds client budget {client.budget_limit}"
            ),
            "suggestion": None if passed else "Request budget approval or split invoice",
            "severity": RuleSeverity.MEDIUM.value if not passed else RuleSeverity.INFO.value,
            "confidence": 95.0,
            "input_data": {"amount": str(invoice.total_amount), "limit": str(client.budget_limit)},
        }

    async def _check_missing_fields(self, invoice) -> dict[str, Any]:
        required = ["vendor_name", "total_amount", "issue_date"]
        missing = [f for f in required if not getattr(invoice, f, None)]
        passed = len(missing) == 0
        return {
            "rule_name": "missing_fields",
            "category": "completeness",
            "passed": passed,
            "reason": "All required fields present" if passed else f"Missing fields: {', '.join(missing)}",
            "suggestion": None if passed else "Obtain missing data from vendor before approval",
            "severity": RuleSeverity.HIGH.value if not passed else RuleSeverity.INFO.value,
            "confidence": 98.0,
            "input_data": {"missing": missing},
        }

    async def _check_currency(self, invoice) -> dict[str, Any]:
        valid_currencies = {"USD", "EUR", "GBP", "CAD", "AUD", "INR"}
        currency = (invoice.currency or "USD").upper()
        passed = currency in valid_currencies
        client_match = True
        if invoice.client_id:
            client = await self.client_repo.get_by_id(invoice.client_id)
            if client and client.currency and client.currency.upper() != currency:
                client_match = False
        passed = passed and client_match
        return {
            "rule_name": "currency_validation",
            "category": "compliance",
            "passed": passed,
            "reason": (
                f"Currency {currency} is valid and matches client"
                if passed
                else f"Currency mismatch or unsupported: {currency}"
            ),
            "suggestion": None if passed else "Convert to client currency or update client settings",
            "severity": RuleSeverity.MEDIUM.value if not passed else RuleSeverity.INFO.value,
            "confidence": 97.0,
            "input_data": {"currency": currency},
        }

    async def _check_invoice_number(self, invoice) -> dict[str, Any]:
        import re

        pattern = re.compile(r"^INV-\d{4}-\d{4,6}$")
        passed = bool(invoice.invoice_number and pattern.match(invoice.invoice_number))
        return {
            "rule_name": "invoice_number_format",
            "category": "format",
            "passed": passed,
            "reason": (
                f"Invoice number {invoice.invoice_number} matches INV-YYYY-NNNN format"
                if passed
                else f"Invoice number '{invoice.invoice_number}' does not match expected format"
            ),
            "suggestion": None if passed else "Regenerate invoice number using standard format",
            "severity": RuleSeverity.LOW.value if not passed else RuleSeverity.INFO.value,
            "confidence": 99.0,
            "input_data": {"invoice_number": invoice.invoice_number},
        }

    async def _check_vendor(self, invoice) -> dict[str, Any]:
        passed = bool(invoice.vendor_name and len(invoice.vendor_name.strip()) >= 2)
        if invoice.client_id and invoice.vendor_name:
            client = await self.client_repo.get_by_id(invoice.client_id)
            if client:
                passed = passed and (
                    client.name.lower() in invoice.vendor_name.lower()
                    or invoice.vendor_name.lower() in client.name.lower()
                )
        return {
            "rule_name": "vendor_validation",
            "category": "vendor",
            "passed": passed,
            "reason": "Vendor name is valid" if passed else "Vendor name missing or too short",
            "suggestion": None if passed else "Confirm vendor identity against client records",
            "severity": RuleSeverity.MEDIUM.value if not passed else RuleSeverity.INFO.value,
            "confidence": 88.0,
            "input_data": {"vendor_name": invoice.vendor_name},
        }

    async def _check_working_hours(self, invoice) -> dict[str, Any]:
        fields = invoice.extracted_fields or {}
        hours = fields.get("hours") or fields.get("regular_hours")
        passed = True
        reason = "Working hours within acceptable range"
        if hours is not None:
            hours_dec = Decimal(str(hours))
            passed = hours_dec <= self.MAX_WEEKLY_HOURS and hours_dec > 0
            reason = (
                f"Hours {hours_dec} within 0-{self.MAX_WEEKLY_HOURS} range"
                if passed
                else f"Hours {hours_dec} exceed maximum {self.MAX_WEEKLY_HOURS}"
            )
        return {
            "rule_name": "working_hours",
            "category": "payroll",
            "passed": passed,
            "reason": reason,
            "suggestion": None if passed else "Verify overtime approval for excess hours",
            "severity": RuleSeverity.MEDIUM.value if not passed else RuleSeverity.INFO.value,
            "confidence": 90.0,
            "input_data": {"hours": str(hours) if hours else None},
        }

    async def _check_tax(self, invoice) -> dict[str, Any]:
        if invoice.subtotal and invoice.tax_amount and invoice.total_amount:
            expected = invoice.subtotal + invoice.tax_amount
            tolerance = Decimal("0.05")
            passed = abs(expected - invoice.total_amount) <= tolerance
            reason = (
                "Tax calculation is consistent"
                if passed
                else f"Subtotal + tax ({expected}) != total ({invoice.total_amount})"
            )
        else:
            passed = True
            reason = "Tax fields not present; skipped detailed validation"
        return {
            "rule_name": "tax_calculation",
            "category": "financial",
            "passed": passed,
            "reason": reason,
            "suggestion": None if passed else "Recalculate tax amount or verify line items",
            "severity": RuleSeverity.HIGH.value if not passed else RuleSeverity.INFO.value,
            "confidence": 94.0,
            "input_data": {
                "subtotal": str(invoice.subtotal),
                "tax": str(invoice.tax_amount),
                "total": str(invoice.total_amount),
            },
        }

    async def _check_po(self, invoice) -> dict[str, Any]:
        fields = invoice.extracted_fields or {}
        has_po = bool(invoice.po_reference or fields.get("po_number"))
        amount = invoice.total_amount or Decimal("0")
        required = amount > Decimal("5000")
        passed = has_po or not required
        return {
            "rule_name": "po_reference",
            "category": "procurement",
            "passed": passed,
            "reason": (
                "PO reference present or not required"
                if passed
                else f"PO required for invoices over $5000 (amount: {amount})"
            ),
            "suggestion": None if passed else "Request PO number from client before processing",
            "severity": RuleSeverity.MEDIUM.value if not passed else RuleSeverity.INFO.value,
            "confidence": 91.0,
            "input_data": {"po_reference": invoice.po_reference, "amount": str(amount)},
        }

    async def _check_salary_limits(self, invoice) -> dict[str, Any]:
        fields = invoice.extracted_fields or {}
        rate = fields.get("rate")
        passed = True
        reason = "Hourly rate within salary limits"
        if rate is not None:
            rate_dec = Decimal(str(rate))
            passed = rate_dec <= self.SALARY_HOURLY_CAP
            reason = (
                f"Rate ${rate_dec}/hr within cap ${self.SALARY_HOURLY_CAP}"
                if passed
                else f"Rate ${rate_dec}/hr exceeds cap ${self.SALARY_HOURLY_CAP}"
            )
        return {
            "rule_name": "salary_limits",
            "category": "payroll",
            "passed": passed,
            "reason": reason,
            "suggestion": None if passed else "Escalate to HR for rate exception approval",
            "severity": RuleSeverity.HIGH.value if not passed else RuleSeverity.INFO.value,
            "confidence": 93.0,
            "input_data": {"rate": str(rate) if rate else None},
        }

    async def _check_client_rules(self, invoice) -> dict[str, Any]:
        active_rules = await self.business_rule_repo.list_active()
        client_rules = [r for r in active_rules if r.category in ("client", "general")]
        if not client_rules:
            return self._skip_rule("client_rules", "client", "No active client business rules configured")

        failed_names: list[str] = []
        for rule in client_rules:
            expr = rule.condition_expression.lower()
            if "budget" in expr and invoice.total_amount and invoice.client_id:
                client = await self.client_repo.get_by_id(invoice.client_id)
                if client and client.budget_limit and invoice.total_amount > client.budget_limit:
                    failed_names.append(rule.name)

        passed = len(failed_names) == 0
        return {
            "rule_name": "client_business_rules",
            "category": "client",
            "passed": passed,
            "reason": (
                "All client business rules satisfied"
                if passed
                else f"Failed rules: {', '.join(failed_names)}"
            ),
            "suggestion": None if passed else "Review client-specific rule violations",
            "severity": RuleSeverity.MEDIUM.value if not passed else RuleSeverity.INFO.value,
            "confidence": 86.0,
            "input_data": {"evaluated_rules": len(client_rules)},
        }

    @staticmethod
    def _skip_rule(name: str, category: str, reason: str) -> dict[str, Any]:
        return {
            "rule_name": name,
            "category": category,
            "passed": True,
            "reason": reason,
            "suggestion": None,
            "severity": RuleSeverity.INFO.value,
            "confidence": 70.0,
            "input_data": {},
        }
