"""Vendor invoice."""

import random
from datetime import timedelta
from faker import Faker
from .base import (
    ocr_space,
    money,
    fmt_date,
    rand_date,
    rand_amount,
    pad,
    table_row,
    non_pii_date,
    non_pii_addr,
    non_pii_company,
    person_company,
    VENDOR_SUFFIXES,
)

DOC_TYPE = "invoice"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []

    vendor, is_person = person_company(fake, VENDOR_SUFFIXES)
    if is_person:
        non_pii.append(non_pii_company(vendor, "vendor_name_resembles_person"))
    vendor_addr = fake.address().replace("\n", ", ")
    vendor_email = fake.company_email()
    vendor_phone = fake.phone_number()
    non_pii.append(non_pii_addr(vendor_addr, "vendor_address"))

    client = fake.name()
    display_name = f"{client}  /  {overlay_name}" if overlay_name else client
    client_co = fake.company()
    client_addr = fake.address().replace("\n", ", ")
    client_email = fake.email()

    inv_num = f"INV-{random.randint(10000, 99999)}"
    inv_date = rand_date(1)
    due_date = inv_date + timedelta(days=random.choice([15, 30, 45]))
    inv_date_str = fmt_date(inv_date)
    due_date_str = fmt_date(due_date)
    non_pii.append(non_pii_date(inv_date_str, "invoice_date"))
    non_pii.append(non_pii_date(due_date_str, "due_date"))

    items = []
    for _ in range(random.randint(3, 7)):
        desc = random.choice(
            [
                "Consulting Services",
                "Software License",
                "Support Package",
                "Implementation Fee",
                "Training Session",
                "Data Migration",
                "API Integration",
                "Monthly Retainer",
                "Project Management",
                "Quality Assurance Testing",
            ]
        )
        qty = random.randint(1, 40)
        unit = rand_amount(50, 800)
        items.append((desc, qty, unit, round(qty * unit, 2)))

    subtotal = sum(i[3] for i in items)
    tax_rate = random.choice([0.0, 0.06, 0.075, 0.08, 0.095])
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)

    item_lines = "\n".join(
        table_row([i[0][:26], i[1], money(i[2]), money(i[3])], [28, 6, 12, 12])
        for i in items
    )

    text = f"""
INVOICE

{vendor}
{vendor_addr}
Phone:  {vendor_phone}
Email:  {vendor_email}

Bill  To:
{display_name}
{client_co}
{client_addr}
{client_email}

Invoice  #:   {inv_num}
Invoice  Date:  {inv_date_str}
Due  Date:      {due_date_str}
Payment  Terms:  Net  {(due_date - inv_date).days}

{"-" * 60}
{table_row(["Description", "Qty", "Unit Price", "Total"], [28, 6, 12, 12])}
{"-" * 60}
{item_lines}
{"-" * 60}
{pad("Subtotal", money(subtotal), 46)}
{pad(f"Tax  ({tax_rate * 100:.1f}%)", money(tax), 46)}
{pad("TOTAL  DUE", money(total), 46)}
{"-" * 60}

Payment  Methods:   Bank  Transfer  |  Check  |  Credit  Card
Remit  to:  {vendor}  •  {vendor_addr}
Questions?  {vendor_email}   {vendor_phone}

Thank  you  for  your  business!
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "client_name": client,
        "client_address": client_addr,
        "client_email": client_email,
        "vendor_phone": vendor_phone,
        "vendor_email": vendor_email,
        "invoice_number": inv_num,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
