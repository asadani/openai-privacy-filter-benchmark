"""Employee pay stub."""

import random
from datetime import timedelta
from faker import Faker
from .base import (
    ocr_space,
    money,
    fmt_date,
    rand_date,
    rand_amount,
    ssn,
    last4,
    pad,
    table_row,
    non_pii_date,
    non_pii_addr,
    non_pii_company,
    person_company,
)

DOC_TYPE = "paystub"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []

    emp = fake.name()
    display_name = f"{emp}  /  {overlay_name}" if overlay_name else emp
    emp_id = f"EMP{random.randint(10000, 99999)}"
    emp_addr = fake.address().replace("\n", ", ")
    emp_ssn = ssn(fake)

    company, is_person = person_company(
        fake, ["Inc.", "Corp.", "LLC", "& Co.", "Staffing"]
    )
    if is_person:
        non_pii.append(non_pii_company(company, "employer_name_resembles_person"))
    co_addr = fake.address().replace("\n", ", ")
    non_pii.append(non_pii_addr(co_addr, "employer_address"))

    pay_date = rand_date(1)
    period_start = pay_date - timedelta(days=14)
    pay_date_str = fmt_date(pay_date)
    period_start_str = fmt_date(period_start)
    non_pii.append(non_pii_date(pay_date_str, "pay_date"))
    non_pii.append(non_pii_date(period_start_str, "pay_period_start"))

    rate = rand_amount(18, 95)
    hours = round(random.uniform(70, 88), 1)
    gross = round(rate * hours, 2)
    fed = round(gross * random.uniform(0.10, 0.22), 2)
    state_tax = round(gross * random.uniform(0.03, 0.08), 2)
    ss = round(gross * 0.062, 2)
    medicare = round(gross * 0.0145, 2)
    health = round(random.uniform(0, 450), 2)
    net = round(gross - fed - state_tax - ss - medicare - health, 2)
    ytd_gross = round(gross * random.uniform(1.5, 26), 2)

    text = f"""
{company}
{co_addr}

PAY  STUB

Employee  Name:   {display_name}
Employee  ID:     {emp_id}
SSN  (last  4):   XXX-XX-{last4(emp_ssn)}
Address:          {emp_addr}

Pay  Date:        {pay_date_str}
Pay  Period:      {period_start_str}  -  {pay_date_str}
Pay  Type:        {"Hourly" if rate < 50 else "Salary"}

{"-" * 56}
EARNINGS
{"-" * 56}
{table_row(["Description", "Rate", "Hours", "Amount"], [22, 10, 8, 12])}
Regular  Pay          {money(rate)}   {hours}    {money(gross)}

{"-" * 56}
{pad("Gross  Pay", money(gross), 40)}
{"-" * 56}

DEDUCTIONS
{table_row(["Description", "Current", "YTD"], [24, 12, 12])}
Federal  Income  Tax    {money(fed)}   {money(round(fed * random.uniform(1.5, 26), 2))}
State  Income  Tax      {money(state_tax)}   {money(round(state_tax * random.uniform(1.5, 26), 2))}
Social  Security        {money(ss)}      {money(round(ss * random.uniform(1.5, 26), 2))}
Medicare                {money(medicare)}    {money(round(medicare * random.uniform(1.5, 26), 2))}
Health  Insurance       {money(health)}   {money(round(health * random.uniform(1.5, 26), 2))}

{"-" * 56}
{pad("Total  Deductions", money(round(fed + state_tax + ss + medicare + health, 2)), 40)}
{pad("NET  PAY", money(net), 40)}
{"-" * 56}

Year-to-Date  Gross:  {money(ytd_gross)}

This  document  is  a  pay  summary  generated  for  payroll  purposes  only.
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "name": emp,
        "employee_id": emp_id,
        "ssn": emp_ssn,
        "address": emp_addr,
        "employer_name": company,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
