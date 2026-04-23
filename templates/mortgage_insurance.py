"""Homeowners / mortgage insurance policy declarations."""

import random
from datetime import timedelta
from faker import Faker
from .base import (
    ocr_space,
    money,
    fmt_date,
    rand_date,
    rand_amount,
    policy_number,
    pad,
    non_pii_date,
    non_pii_company,
    person_company,
    INSURER_SUFFIXES,
    LENDER_SUFFIXES,
)

DOC_TYPE = "mortgage_insurance"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []

    insured = fake.name()
    display_name = f"{insured}  /  {overlay_name}" if overlay_name else insured
    prop_addr = fake.address().replace("\n", ", ")
    mail_addr = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()

    insurer, ins_is_person = person_company(fake, INSURER_SUFFIXES)
    if ins_is_person:
        non_pii.append(non_pii_company(insurer, "insurer_name_resembles_person"))

    agent = fake.name()  # real person — stays in pii_gt
    agent_phone = fake.phone_number()

    lender, lender_is_person = person_company(fake, LENDER_SUFFIXES)
    if lender_is_person:
        non_pii.append(non_pii_company(lender, "lender_name_resembles_person"))

    pol_num = policy_number()
    loan_num = f"LN{random.randint(1000000000, 9999999999)}"

    eff_date = rand_date(2)
    exp_date = eff_date + timedelta(days=365)
    eff_str = fmt_date(eff_date)
    exp_str = fmt_date(exp_date)
    non_pii.append(non_pii_date(eff_str, "policy_effective_date"))
    non_pii.append(non_pii_date(exp_str, "policy_expiration_date"))

    dwelling = rand_amount(180000, 950000)
    personal_prop = round(dwelling * 0.5, 2)
    liability = round(random.choice([100000, 300000, 500000]), 2)
    deductible = random.choice([500, 1000, 2500, 5000])
    annual_prem = rand_amount(800, 4200)

    text = f"""
HOMEOWNERS  INSURANCE  POLICY  DECLARATIONS

{insurer}
Policy  Number:  {pol_num}
Policy  Period:  {eff_str}  12:01  AM  to  {exp_str}  12:01  AM

NAMED  INSURED  AND  MAILING  ADDRESS
{display_name}
{mail_addr}
Phone:  {phone}
Email:  {email}

PROPERTY  INSURED
Location:  {prop_addr}

MORTGAGEE  /  LOSS  PAYEE
{lender}
Loan  Number:  {loan_num}

YOUR  AGENT
{agent}
Phone:  {agent_phone}

COVERAGES  AND  LIMITS
{"-" * 52}
{pad("A  -  Dwelling", money(dwelling), 46)}
{pad("B  -  Other  Structures", money(round(dwelling * 0.1, 2)), 46)}
{pad("C  -  Personal  Property", money(personal_prop), 46)}
{pad("D  -  Loss  of  Use", money(round(dwelling * 0.2, 2)), 46)}
{pad("E  -  Personal  Liability", money(liability), 46)}
{pad("F  -  Medical  Payments", money(5000), 46)}
{"-" * 52}
{pad("All  Peril  Deductible", f"${deductible:,}", 46)}

PREMIUM  SUMMARY
{pad("Annual  Premium", money(annual_prem), 46)}
{pad("Monthly  Installment", money(round(annual_prem / 12, 2)), 46)}

This  declarations  page  is  part  of  your  policy  contract.  Please  read  your
policy  carefully.  Coverage  is  subject  to  the  terms,  conditions,  and
exclusions  of  the  policy.  In  the  event  of  a  claim  contact  {insurer}
at  the  number  on  file  with  your  agent  {agent}  ({agent_phone}).
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "name": insured,
        "mailing_address": mail_addr,
        "property_address": prop_addr,
        "phone": phone,
        "email": email,
        "policy_number": pol_num,
        "loan_number": loan_num,
        "agent_name": agent,
        "agent_phone": agent_phone,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
