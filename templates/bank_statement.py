"""Bank account statement."""

import random
from datetime import timedelta
from faker import Faker
from .base import (
    ocr_space,
    money,
    fmt_date,
    rand_date,
    rand_amount,
    account_num,
    routing_num,
    last4,
    pad,
    table_row,
    non_pii_date,
    non_pii_company,
    person_company,
    BANK_SUFFIXES,
)

DOC_TYPE = "bank_statement"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []

    holder = fake.name()
    display_name = f"{holder}  /  {overlay_name}" if overlay_name else holder
    addr = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    acct = account_num()
    routing = routing_num()

    bank, is_person = person_company(fake, BANK_SUFFIXES)
    if is_person:
        non_pii.append(non_pii_company(bank, "bank_name_resembles_person"))

    stmt_date = rand_date(1)
    period_start = stmt_date - timedelta(days=30)
    stmt_date_str = fmt_date(stmt_date)
    period_start_str = fmt_date(period_start)
    non_pii.append(non_pii_date(stmt_date_str, "statement_date"))
    non_pii.append(non_pii_date(period_start_str, "statement_period_start"))

    balance_open = rand_amount(500, 25000)
    txns = []
    running = balance_open
    for _ in range(random.randint(8, 14)):
        txn_date = period_start + timedelta(days=random.randint(0, 29))
        is_credit = random.random() < 0.35
        amt = rand_amount(5, 3500)
        running += amt if is_credit else -amt
        desc = random.choice(
            [
                fake.company(),
                "ACH DEPOSIT",
                "ATM WITHDRAWAL",
                "ONLINE TRANSFER",
                "BILL PAYMENT",
                "POINT OF SALE",
                "DIRECT DEPOSIT",
                fake.city() + " PURCHASE",
            ]
        )
        txn_date_str = fmt_date(txn_date)
        non_pii.append(non_pii_date(txn_date_str, "transaction_date"))
        txns.append((txn_date_str, desc, is_credit, amt, max(running, 0)))

    txn_lines = "\n".join(
        table_row(
            [t[0], t[1][:28], ("+" if t[2] else "-") + money(t[3]), money(t[4])],
            [12, 30, 14, 14],
        )
        for t in txns
    )
    balance_close = txns[-1][4] if txns else balance_open

    text = f"""
{bank}
Member FDIC     Equal Housing Lender

ACCOUNT  STATEMENT
Statement  Period:  {period_start_str}  to  {stmt_date_str}

Account  Holder
{display_name}
{addr}
Phone:  {phone}
Email:  {email}

CHECKING  ACCOUNT
Account  Number:  ****{last4(acct)}
Routing  Number:  {routing}
Full  Account  (for  wires):  {acct}

{pad("Opening  Balance", money(balance_open))}
{pad("Total  Credits", money(sum(t[3] for t in txns if t[2])))}
{pad("Total  Debits", money(sum(t[3] for t in txns if not t[2])))}
{pad("Closing  Balance", money(balance_close))}

TRANSACTION  HISTORY
{table_row(["Date", "Description", "Amount", "Balance"], [12, 30, 14, 14])}
{"-" * 74}
{txn_lines}

Thank  you  for  banking  with  {bank}.
For  questions  call  {phone}  or  visit  your  nearest  branch.
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "name": holder,
        "address": addr,
        "phone": phone,
        "email": email,
        "account_number": acct,
        "routing_number": routing,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
