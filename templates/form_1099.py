"""Form 1099 (NEC, MISC, INT, DIV)."""

import random
from faker import Faker
from .base import (
    ocr_space,
    money,
    rand_amount,
    ssn,
    ein,
    last4,
    non_pii_addr,
    non_pii_company,
    person_company,
)

DOC_TYPE = "1099"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []
    form_type = random.choice(["NEC", "MISC", "INT", "DIV"])

    recipient = fake.name()
    display_name = f"{recipient}  /  {overlay_name}" if overlay_name else recipient
    rec_ssn = ssn(fake)
    rec_addr = fake.address().replace("\n", ", ")

    payer, is_person = person_company(
        fake, ["LLC", "Inc.", "Corp.", "& Partners", "Group"]
    )
    if is_person:
        non_pii.append(non_pii_company(payer, "payer_name_resembles_person"))
    payer_ein = ein()
    payer_addr = fake.address().replace("\n", ", ")
    non_pii.append(non_pii_addr(payer_addr, "payer_address"))

    tax_year = random.randint(2020, 2024)
    amount = rand_amount(500, 95000)
    fed_tax = round(amount * random.uniform(0, 0.24), 2)
    account = f"{random.randint(1000, 9999)}-{random.randint(100, 999)}"

    box_label = {
        "NEC": "1  Nonemployee compensation",
        "MISC": "3  Other income",
        "INT": "1  Interest income",
        "DIV": "1a  Total ordinary dividends",
    }[form_type]

    text = f"""
Form  1099-{form_type}      (Rev. January {tax_year})
OMB No.  1545-{random.randint(1000, 9999)}         {tax_year}

PAYER'S name, street address, city, state, ZIP
{payer}
{payer_addr}

PAYER'S  TIN          RECIPIENT'S  TIN
{payer_ein}            XXX-XX-{last4(rec_ssn)}

RECIPIENT'S  name
{display_name}

Street  address  (including  apt. no.)
{rec_addr}

Account  number  (see  instructions)
{account}

{box_label}
{money(amount)}

4   Federal  income  tax  withheld
{money(fed_tax)}

FATCA  filing  requirement  [ ]

This  is  important  tax  information and  is  being  furnished  to  the  IRS.
If  you  are  required  to  file  a  return,  a  negligence  penalty  or  other
sanction  may  be  imposed  on  you  if  this  income  is  taxable  and  the  IRS
determines  that  it  has  not  been  reported.
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "name": recipient,
        "ssn": rec_ssn,
        "address": rec_addr,
        "payer_ein": payer_ein,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
