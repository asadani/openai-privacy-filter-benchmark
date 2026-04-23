"""Shared helpers, constants, and non-PII factory functions for all document templates."""

import re
import random
from datetime import date, timedelta

__all__ = [
    "ocr_space",
    "money",
    "fmt_date",
    "rand_date",
    "rand_amount",
    "ssn",
    "ein",
    "last4",
    "vin_number",
    "license_plate",
    "policy_number",
    "account_num",
    "routing_num",
    "pad",
    "table_row",
    "word_count",
    "non_pii_date",
    "non_pii_addr",
    "non_pii_company",
    "person_company",
    "INSURER_SUFFIXES",
    "LENDER_SUFFIXES",
    "VENDOR_SUFFIXES",
    "BANK_SUFFIXES",
]

INSURER_SUFFIXES = [
    "Insurance Co.",
    "Insurance Group",
    "Insurance Agency",
    "Mutual Insurance",
    "& Sons Insurance",
]
LENDER_SUFFIXES = [
    "Mortgage",
    "Mortgage Group",
    "Home Loans",
    "Mortgage Services",
    "Lending Co.",
]
VENDOR_SUFFIXES = [
    "& Associates",
    "Consulting",
    "Solutions",
    "Services Group",
    "Advisory",
]
BANK_SUFFIXES = [
    "Community Bank",
    "National Bank",
    "Savings Bank",
    "Financial",
    "Trust Bank",
]


def ocr_space(text: str) -> str:
    """Add light OCR-style spacing artifacts to simulate scanned document noise."""
    lines = text.split("\n")
    out = []
    for line in lines:
        if random.random() < 0.12:
            line = "  " + line
        if random.random() < 0.08:
            line = line + "  "
        if random.random() < 0.18 and len(line) > 12:
            pos = random.randint(6, max(7, len(line) - 6))
            line = line[:pos] + "  " + line[pos:]
        out.append(line)
    return "\n".join(out)


def money(amount: float) -> str:
    return random.choice([f"${amount:,.2f}", f"$ {amount:,.2f}", f"{amount:,.2f}"])


def fmt_date(d: date) -> str:
    return random.choice(
        [
            d.strftime("%m/%d/%Y"),
            d.strftime("%B %d, %Y"),
            d.strftime("%d-%b-%Y"),
            d.strftime("%Y-%m-%d"),
        ]
    )


def rand_date(years_back: int = 3) -> date:
    start = date.today() - timedelta(days=years_back * 365)
    return start + timedelta(days=random.randint(0, years_back * 365))


def rand_amount(lo: float, hi: float) -> float:
    return round(random.uniform(lo, hi), 2)


def ssn(fake) -> str:
    return fake.ssn()


def ein() -> str:
    return f"{random.randint(10, 99)}-{random.randint(1000000, 9999999)}"


def last4(s: str) -> str:
    digits = re.sub(r"\D", "", s)
    return digits[-4:] if len(digits) >= 4 else digits


def vin_number() -> str:
    chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    return "".join(random.choices(chars, k=17))


def license_plate() -> str:
    return (
        "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=3))
        + str(random.randint(100, 999))
        + "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=2))
    )


def policy_number() -> str:
    prefix = random.choice(["POL", "INS", "AUTO", "MRT", "HME"])
    return f"{prefix}-{random.randint(100000, 999999)}-{random.randint(10, 99)}"


def account_num() -> str:
    return str(random.randint(1000000000, 9999999999))


def routing_num() -> str:
    return f"{random.randint(21000000, 121999999):09d}"


def pad(label: str, value: str, width: int = 38) -> str:
    dots = "." * max(1, width - len(label) - len(value))
    return f"{label}{dots}{value}"


def table_row(cols: list, widths: list) -> str:
    return "  ".join(str(c).ljust(w) for c, w in zip(cols, widths))


def word_count(text: str) -> int:
    return len(text.split())


# ---------------------------------------------------------------------------
# non_pii_data entry factories — values the model should NOT flag
# ---------------------------------------------------------------------------


def non_pii_date(value: str, reason: str) -> dict:
    """Administrative date: invoice date, pay date, policy period, etc."""
    return {"type": "date", "value": value, "reason": reason}


def non_pii_addr(value: str, reason: str) -> dict:
    """Business address: employer, vendor, insurer — not a private residence."""
    return {"type": "address", "value": value, "reason": reason}


def non_pii_company(value: str, reason: str) -> dict:
    """Company name that visually resembles a person name, e.g. 'Williams Insurance Co.'"""
    return {"type": "company_name", "value": value, "reason": reason}


def person_company(fake, suffixes: list[str]) -> tuple[str, bool]:
    """
    Return (company_name, is_person_like).
    ~60 % of the time uses a last name as the root so the name looks like a person.
    """
    if random.random() < 0.60:
        return f"{fake.last_name()} {random.choice(suffixes)}", True
    return fake.company(), False
