"""Email domain and security utilities."""

import re
from email.utils import parseaddr


def extract_domain(email: str) -> str | None:
    _, addr = parseaddr(email)
    if "@" in addr:
        return addr.split("@")[1].lower()
    return None


def extract_invoice_number(text: str) -> str | None:
    patterns = [
        r"INV[-\s]?(\d{3,6})",
        r"Invoice\s*#?\s*(\d{3,6})",
        r"INV-(\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            num = match.group(1) if match.lastindex else match.group(0)
            return f"INV-{num}" if not num.startswith("INV") else num.replace(" ", "-")
    return None


def detect_spam_signals(subject: str, body: str, from_email: str) -> tuple[bool, list[str]]:
    signals = []
    text = f"{subject} {body}".lower()
    urgent_patterns = ["urgent", "wire transfer", "immediately", "act now", "verify account"]
    for p in urgent_patterns:
        if p in text:
            signals.append(f"urgent_keyword:{p}")
    if from_email and "unknown" in from_email.lower():
        signals.append("unknown_sender_domain")
    if re.search(r"\$\d{1,3}(,\d{3})+\.\d{2}", text) and "invoice" not in text:
        signals.append("amount_without_invoice_context")
    return len(signals) >= 2, signals


def compute_risk_level(score: float) -> str:
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    if score >= 40:
        return "high"
    return "critical"


def format_currency(amount: float | None, currency: str = "USD") -> str:
    if amount is None:
        return "N/A"
    symbol = "$" if currency == "USD" else currency + " "
    return f"{symbol}{amount:,.2f}"
