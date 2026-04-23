"""Automobile insurance policy declarations."""

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
    vin_number,
    license_plate,
    pad,
    non_pii_date,
    non_pii_company,
    person_company,
    INSURER_SUFFIXES,
)

DOC_TYPE = "auto_insurance"


def generate(fake: Faker, overlay_name: str | None = None) -> tuple[str, dict, list]:
    non_pii = []

    insured = fake.name()
    display_name = f"{insured}  /  {overlay_name}" if overlay_name else insured
    addr = fake.address().replace("\n", ", ")
    phone = fake.phone_number()
    email = fake.email()
    dob = fake.date_of_birth(minimum_age=18, maximum_age=75)
    dob_str = fmt_date(dob)  # personal PII — goes in pii_gt, not non_pii
    license_no = "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ", k=1)) + str(
        random.randint(1000000, 9999999)
    )

    insurer, is_person = person_company(fake, INSURER_SUFFIXES)
    if is_person:
        non_pii.append(non_pii_company(insurer, "insurer_name_resembles_person"))

    agent = fake.name()
    agent_phone = fake.phone_number()
    pol_num = policy_number()

    eff_date = rand_date(1)
    exp_date = eff_date + timedelta(days=180)
    eff_str = fmt_date(eff_date)
    exp_str = fmt_date(exp_date)
    non_pii.append(non_pii_date(eff_str, "policy_effective_date"))
    non_pii.append(non_pii_date(exp_str, "policy_expiration_date"))

    vehicles = []
    for _ in range(random.randint(1, 2)):
        yr = random.randint(2008, 2024)
        make = random.choice(
            [
                "Toyota",
                "Honda",
                "Ford",
                "Chevrolet",
                "BMW",
                "Hyundai",
                "Nissan",
                "Subaru",
                "Volkswagen",
                "Kia",
            ]
        )
        model = random.choice(
            [
                "Camry",
                "Civic",
                "F-150",
                "Malibu",
                "3 Series",
                "Elantra",
                "Altima",
                "Outback",
                "Jetta",
                "Sorento",
            ]
        )
        vehicles.append(
            {
                "year": yr,
                "make": make,
                "model": model,
                "vin": vin_number(),
                "plate": license_plate(),
            }
        )

    vehicle_blocks = ""
    for v in vehicles:
        vehicle_blocks += (
            f"\nVehicle:  {v['year']}  {v['make']}  {v['model']}"
            f"\nVIN:      {v['vin']}"
            f"\nPlate:    {v['plate']}\n"
        )

    bi = random.choice([25000, 50000, 100000, 250000, 500000])
    pd = random.choice([25000, 50000, 100000])
    um = random.choice([25000, 50000, 100000])
    comp = random.choice([250, 500, 1000])
    coll = random.choice([250, 500, 1000])
    prem = rand_amount(600, 3200)
    discounts = "  ".join(
        filter(None, [
            "Multi-policy" if random.random() > 0.5 else "",
            "Safe  driver" if random.random() > 0.5 else "",
            "Good  student" if random.random() > 0.5 else "",
        ])
    )

    text = f"""
AUTOMOBILE  INSURANCE  POLICY  DECLARATIONS

{insurer}

Policy  Number:  {pol_num}
Policy  Period:  {eff_str}  to  {exp_str}

NAMED  INSURED
{display_name}
{addr}
Date  of  Birth:  {dob_str}
Driver  License:  {license_no}
Phone:  {phone}
Email:  {email}
{vehicle_blocks}
YOUR  AGENT
{agent}
{agent_phone}

COVERAGE  SUMMARY
{"-" * 54}
{pad("Bodily  Injury  Liability", f"${bi:,}/${bi * 2:,}", 44)}
{pad("Property  Damage  Liability", f"${pd:,}", 44)}
{pad("Uninsured  Motorist  BI", f"${um:,}/${um * 2:,}", 44)}
{pad("Comprehensive  Deductible", f"${comp:,}", 44)}
{pad("Collision  Deductible", f"${coll:,}", 44)}
{"-" * 54}
{pad("6-Month  Premium", money(prem), 44)}
{pad("Monthly  Installment", money(round(prem / 6, 2)), 44)}

Discounts  Applied:  {discounts}

This  policy  is  issued  subject  to  all  terms  and  conditions.  Contact  your
agent  {agent}  at  {agent_phone}  with  any  questions  or  to  make  changes.
"""
    text = ocr_space(text.strip())
    pii_gt = {
        "name": insured,
        "address": addr,
        "phone": phone,
        "email": email,
        "date_of_birth": dob_str,
        "driver_license": license_no,
        "policy_number": pol_num,
        "vin": [v["vin"] for v in vehicles],
        "license_plate": [v["plate"] for v in vehicles],
        "agent_name": agent,
        "agent_phone": agent_phone,
    }
    if overlay_name:
        pii_gt["name_native_script"] = overlay_name
    return text, pii_gt, non_pii
