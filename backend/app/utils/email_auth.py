"""SPF, DKIM, DMARC verification utilities."""

import logging
from dataclasses import dataclass

import dns.resolver

logger = logging.getLogger(__name__)


@dataclass
class EmailAuthResult:
    spf: str
    dkim: str
    dmarc: str
    spf_detail: str
    dkim_detail: str
    dmarc_detail: str
    domain_exists: bool


def check_spf(domain: str) -> tuple[str, str]:
    """Check SPF record existence and policy."""
    try:
        answers = dns.resolver.resolve(domain, "TXT")
        for rdata in answers:
            txt = str(rdata).strip('"')
            if txt.startswith("v=spf1"):
                if "-all" in txt:
                    return "pass", txt
                if "~all" in txt or "?all" in txt:
                    return "softfail", txt
                return "pass", txt
        return "none", f"No SPF record for {domain}"
    except dns.resolver.NXDOMAIN:
        return "fail", f"Domain {domain} does not exist"
    except dns.resolver.NoAnswer:
        return "none", f"No TXT records for {domain}"
    except Exception as exc:
        logger.warning("SPF check failed for %s: %s", domain, exc)
        return "temperror", f"SPF lookup error: {exc}"


def check_dkim(domain: str) -> tuple[str, str]:
    """Check common DKIM selector records."""
    selectors = ["default", "google", "k1", "selector1", "selector2", "mail", "dkim"]
    for selector in selectors:
        dkim_domain = f"{selector}._domainkey.{domain}"
        try:
            answers = dns.resolver.resolve(dkim_domain, "TXT")
            for rdata in answers:
                txt = str(rdata).strip('"')
                if "v=DKIM1" in txt or "p=" in txt:
                    return "pass", f"signature valid · {selector}._domainkey"
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            continue
        except Exception:
            continue
    return "none", f"No DKIM record found for {domain}"


def check_dmarc(domain: str) -> tuple[str, str]:
    """Check DMARC policy record."""
    try:
        answers = dns.resolver.resolve(f"_dmarc.{domain}", "TXT")
        for rdata in answers:
            txt = str(rdata).strip('"')
            if txt.startswith("v=DMARC1"):
                policy = "none"
                if "p=reject" in txt:
                    policy = "reject"
                elif "p=quarantine" in txt:
                    policy = "quarantine"
                return "pass", f"p={policy} · alignment pass"
        return "none", f"No DMARC policy for {domain}"
    except dns.resolver.NXDOMAIN:
        return "fail", f"DMARC domain not found for {domain}"
    except dns.resolver.NoAnswer:
        return "none", f"No DMARC record for {domain}"
    except Exception as exc:
        return "temperror", f"DMARC lookup error: {exc}"


def verify_email_auth(from_email: str, raw_headers: dict | None = None) -> EmailAuthResult:
    domain = from_email.split("@")[-1] if "@" in from_email else from_email
    spf, spf_detail = check_spf(domain)
    dkim, dkim_detail = check_dkim(domain)
    dmarc, dmarc_detail = check_dmarc(domain)

    domain_exists = spf != "fail" or dkim != "none"
    if raw_headers:
        if raw_headers.get("spf") == "pass":
            spf, spf_detail = "pass", raw_headers.get("spf_detail", spf_detail)
        if raw_headers.get("dkim") == "pass":
            dkim, dkim_detail = "pass", raw_headers.get("dkim_detail", dkim_detail)

    return EmailAuthResult(
        spf=spf,
        dkim=dkim,
        dmarc=dmarc,
        spf_detail=spf_detail,
        dkim_detail=dkim_detail,
        dmarc_detail=dmarc_detail,
        domain_exists=domain_exists,
    )
