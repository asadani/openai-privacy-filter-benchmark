"""W-2 Wage and Tax Statement."""

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

DOC_TYPE = "w2"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []

    emp_name = fake.name()
    display_name = f"{emp_name}  /  {overlay_name}" if overlay_name else emp_name
    emp_addr = fake.address().replace("\n", ", ")
    emp_ssn = ssn(fake)

    employer, is_person = person_company(
        fake, ["Inc.", "Corp.", "LLC", "& Co.", "Group"]
    )
    if is_person:
        non_pii.append(non_pii_company(employer, "employer_name_resembles_person"))
    emp_ein = ein()
    emp_addr2 = fake.address().replace("\n", ", ")
    non_pii.append(non_pii_addr(emp_addr2, "employer_address"))

    tax_year = random.randint(2020, 2024)
    wages = rand_amount(28000, 185000)
    fed_tax = round(wages * random.uniform(0.12, 0.24), 2)
    state_tax = round(wages * random.uniform(0.03, 0.09), 2)
    ss_wages = min(wages, 160200)
    ss_tax = round(ss_wages * 0.062, 2)
    medicare = round(wages * 0.0145, 2)
    state = fake.state_abbr() if hasattr(fake, "state_abbr") else "CA"
    state_id = f"{state}-{random.randint(10000000, 99999999)}"

    text = f"""
W-2  Wage and  Tax  Statement          {tax_year}
OMB No. 1545-0008

a   Employee's social security number
    XXX-XX-{last4(emp_ssn)}

b   Employer identification number (EIN)
    {emp_ein}

c   Employer's name, address, and ZIP code
    {employer}
    {emp_addr2}

d   Control number
    {random.randint(1000, 9999):04d}-{random.randint(100, 999)}

e   Employee's first name and initial     Last name         Suf.
    {display_name}

f   Employee's address and ZIP code
    {emp_addr}

1   Wages, tips, other compensation       2   Federal income tax withheld
    {money(wages)}                            {money(fed_tax)}

3   Social security wages                 4   Social security tax withheld
    {money(ss_wages)}                         {money(ss_tax)}

5   Medicare wages and tips               6   Medicare tax withheld
    {money(wages)}                            {money(medicare)}

15  State    Employer's state ID number   16  State wages     17  State income tax
    {state}       {state_id}                  {money(wages)}      {money(state_tax)}

Copy B — To Be Filed With Employee's FEDERAL Tax Return
This information is being furnished to the Internal Revenue Service.
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "name": emp_name,
        "ssn": emp_ssn,
        "address": emp_addr,
        "employer_ein": emp_ein,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
