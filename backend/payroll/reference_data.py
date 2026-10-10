"""
Initial payroll settings for Cameroon. They are data, not code: they are
loaded once into the database and then maintained by the payroll officer as
dated versions (BN-89). Values marked "to validate" must be confirmed by the
HR and payroll department before the first real payroll (OP-01).
"""

import datetime
from decimal import Decimal

START = datetime.date(2000, 1, 1)

# code: (name, value, unit, description)
PARAMETERS = {
    "SMIG": (
        "Minimum wage (monthly)",
        "41875",
        "AMOUNT",
        "Guaranteed minimum wage – to validate.",
    ),
    "LEGAL_WEEKLY_HOURS": (
        "Legal weekly working time",
        "40",
        "NUMBER",
        "Hours per week.",
    ),
    "HOURS_PER_MONTH": (
        "Hours per month",
        "173.33",
        "NUMBER",
        "Used for the hourly rate.",
    ),
    "ABSENCE_DAY_DIVISOR": (
        "Working days per month",
        "22",
        "NUMBER",
        "Base / divisor = value of one day of absence.",
    ),
    "OT_TIER1_HOURS": (
        "Overtime tier 1 (hours per week)",
        "8",
        "NUMBER",
        "41st to 48th hour (decree 68/DF/249).",
    ),
    "OT_TIER2_HOURS": (
        "Overtime tier 2 (hours per week)",
        "8",
        "NUMBER",
        "49th to 56th hour.",
    ),
    "OT_RATE_TIER1": ("Overtime increase – tier 1", "20", "PERCENT", ""),
    "OT_RATE_TIER2": ("Overtime increase – tier 2", "30", "PERCENT", ""),
    "OT_RATE_TIER3": ("Overtime increase – beyond", "40", "PERCENT", ""),
    "OT_RATE_NIGHT": ("Night overtime increase", "50", "PERCENT", ""),
    "OT_RATE_REST_DAY": ("Rest day work increase", "40", "PERCENT", ""),
    "OT_RATE_HOLIDAY": ("Public holiday work increase", "40", "PERCENT", ""),
    "CNPS_CEILING": (
        "CNPS monthly ceiling",
        "750000",
        "AMOUNT",
        "Ceiling of the contributory base.",
    ),
    "IRPP_ABATEMENT_RATE": (
        "Professional expenses abatement",
        "30",
        "PERCENT",
        "Deducted from the taxable salary.",
    ),
    "IRPP_ANNUAL_ABATEMENT": ("Annual flat abatement", "500000", "AMOUNT", ""),
    "IRPP_EXEMPTION_THRESHOLD": (
        "Income tax exemption threshold (monthly)",
        "62000",
        "AMOUNT",
        "",
    ),
    "SENIORITY_MIN_YEARS": (
        "Seniority bonus – minimum years",
        "2",
        "NUMBER",
        "To validate with the collective agreement.",
    ),
    "SENIORITY_FIRST_RATE": (
        "Seniority bonus – first rate",
        "4",
        "PERCENT",
        "To validate.",
    ),
    "SENIORITY_STEP_RATE": (
        "Seniority bonus – rate per 2 more years",
        "2",
        "PERCENT",
        "To validate.",
    ),
    "BIK_HOUSING_RATE": (
        "Benefit in kind – housing",
        "15",
        "PERCENT",
        "Of the cash taxable salary.",
    ),
    "BIK_ELECTRICITY_RATE": ("Benefit in kind – electricity", "4", "PERCENT", ""),
    "BIK_WATER_RATE": ("Benefit in kind – water", "2", "PERCENT", ""),
    "BIK_DOMESTIC_RATE": (
        "Benefit in kind – domestic staff",
        "5",
        "PERCENT",
        "Per domestic.",
    ),
    "BIK_VEHICLE_RATE": ("Benefit in kind – vehicle", "10", "PERCENT", ""),
    "BIK_FOOD_RATE": ("Benefit in kind – food", "10", "PERCENT", ""),
    "VARIATION_ALERT_PERCENT": (
        "Significant variation threshold",
        "10",
        "PERCENT",
        "BN-107.",
    ),
    "BACK_PAY_LOOKBACK_MONTHS": (
        "Back pay – months examined",
        "12",
        "NUMBER",
        "BN-100.",
    ),
    "NOTICE_DAY_DIVISOR": (
        "Notice indemnity divisor",
        "30",
        "NUMBER",
        "Base / divisor x notice days.",
    ),
    "SEVERANCE_MIN_YEARS": (
        "Severance – minimum seniority",
        "2",
        "NUMBER",
        "To validate.",
    ),
}

# code: (name, kind, brackets)
SCALES = {
    "IRPP": (
        "Income tax (annual)",
        "PROGRESSIVE",
        [
            {"from": 0, "to": 2000000, "rate": 10},
            {"from": 2000000, "to": 3000000, "rate": 15},
            {"from": 3000000, "to": 5000000, "rate": 25},
            {"from": 5000000, "to": None, "rate": 35},
        ],
    ),
    "CRTV": (
        "Audiovisual fee (monthly)",
        "FLAT",
        [
            {"from": 0, "to": 50000, "amount": 0},
            {"from": 50001, "to": 100000, "amount": 750},
            {"from": 100001, "to": 200000, "amount": 1950},
            {"from": 200001, "to": 300000, "amount": 3250},
            {"from": 300001, "to": 400000, "amount": 4550},
            {"from": 400001, "to": 500000, "amount": 5850},
            {"from": 500001, "to": 600000, "amount": 7150},
            {"from": 600001, "to": 700000, "amount": 8450},
            {"from": 700001, "to": 800000, "amount": 9750},
            {"from": 800001, "to": 900000, "amount": 11050},
            {"from": 900001, "to": 1000000, "amount": 12350},
            {"from": 1000001, "to": None, "amount": 13000},
        ],
    ),
    "TDL": (
        "Local development tax (monthly)",
        "FLAT",
        [
            {"from": 0, "to": 62000, "amount": 0},
            {"from": 62001, "to": 75000, "amount": 250},
            {"from": 75001, "to": 100000, "amount": 500},
            {"from": 100001, "to": 125000, "amount": 750},
            {"from": 125001, "to": 150000, "amount": 1000},
            {"from": 150001, "to": 200000, "amount": 1250},
            {"from": 200001, "to": 250000, "amount": 1500},
            {"from": 250001, "to": 300000, "amount": 2000},
            {"from": 300001, "to": 500000, "amount": 2250},
            {"from": 500001, "to": None, "amount": 2500},
        ],
    ),
    "NOTICE_DAYS": (
        "Notice period (days) by years of seniority – to validate with the agreement",
        "FLAT",
        [
            {"from": 0, "to": 0.9999, "amount": 15},
            {"from": 1, "to": 4.9999, "amount": 30},
            {"from": 5, "to": 9.9999, "amount": 60},
            {"from": 10, "to": 14.9999, "amount": 90},
            {"from": 15, "to": None, "amount": 120},
        ],
    ),
    "SEVERANCE": (
        "Severance – % of monthly salary per year of seniority (to validate)",
        "PROGRESSIVE",
        [
            {"from": 0, "to": 5, "rate": 20},
            {"from": 5, "to": 10, "rate": 25},
            {"from": 10, "to": 15, "rate": 30},
            {"from": 15, "to": None, "rate": 35},
        ],
    ),
}

IRPP_BASE = (
    "if_(TAXABLE >= IRPP_EXEMPTION_THRESHOLD, "
    "max(0, (TAXABLE * (100 - IRPP_ABATEMENT_RATE) / 100 - PVID) * 12 - IRPP_ANNUAL_ABATEMENT), 0)"
)

# code: dict of StatutoryDeduction fields
DEDUCTIONS = {
    "PVID": dict(
        name="CNPS – Old age pension (PVID)",
        body="CNPS",
        method="RATE",
        base_formula="min(CONTRIBUTORY, CNPS_CEILING)",
        employee_rate="4.2",
        employer_rate="4.2",
        order=10,
    ),
    "PF": dict(
        name="CNPS – Family allowances",
        body="CNPS",
        method="RATE",
        base_formula="min(CONTRIBUTORY, CNPS_CEILING)",
        employer_rate="7",
        order=11,
    ),
    "AT": dict(
        name="CNPS – Occupational risks",
        body="CNPS",
        method="RATE",
        base_formula="min(CONTRIBUTORY, CNPS_CEILING)",
        employer_rate="1.75",
        order=12,
    ),
    "CFC": dict(
        name="Crédit Foncier",
        body="CFC",
        method="RATE",
        base_formula="TAXABLE",
        employee_rate="1",
        employer_rate="1.5",
        order=20,
    ),
    "FNE": dict(
        name="National Employment Fund",
        body="FNE",
        method="RATE",
        base_formula="TAXABLE",
        employer_rate="1",
        order=21,
    ),
    "IRPP": dict(
        name="Income tax (IRPP)",
        body="TAX",
        method="SCALE",
        base_formula=IRPP_BASE,
        scale_code="IRPP",
        result_divisor="12",
        order=30,
    ),
    "CAC": dict(
        name="Additional council tax (CAC)",
        body="TAX",
        method="PERCENT_OF",
        percent_of_code="IRPP",
        employee_rate="10",
        order=31,
    ),
    "CRTV": dict(
        name="Audiovisual fee (RAV)",
        body="CRTV",
        method="SCALE",
        base_formula="TAXABLE",
        scale_code="CRTV",
        order=32,
    ),
    "TDL": dict(
        name="Local development tax (TDL)",
        body="COMMUNE",
        method="SCALE",
        base_formula="BASE",
        scale_code="TDL",
        order=33,
    ),
}


# code: dict of SalaryElement fields
def _ot(name, rate_param, order):
    return dict(
        name=name,
        kind="GAIN",
        method="QUANTITY",
        is_system=True,
        payslip_order=order,
        formula=f"HOURLY_RATE * (1 + {rate_param} / 100)",
        prorated=False,
    )


def _bik(name, rate_param, order):
    return dict(
        name=name,
        kind="GAIN",
        method="FORMULA",
        formula=f"CASH_TAXABLE * {rate_param} / 100",
        is_benefit_in_kind=True,
        in_leave_allowance_base=False,
        prorated=False,
        payslip_order=order,
    )


ELEMENTS = {
    "BASE": dict(
        name="Base salary",
        kind="GAIN",
        method="FORMULA",
        formula="BASE",
        applies_to_all=True,
        is_system=True,
        payslip_order=10,
    ),
    "SENIORITY": dict(
        name="Seniority bonus",
        kind="GAIN",
        method="FORMULA",
        applies_to_all=True,
        payslip_order=20,
        formula="if_(SENIORITY_YEARS >= SENIORITY_MIN_YEARS, BASE * (SENIORITY_FIRST_RATE + "
        "(floor(SENIORITY_YEARS / 2) - 1) * SENIORITY_STEP_RATE) / 100, 0)",
    ),
    "OT_TIER1": _ot("Overtime – tier 1", "OT_RATE_TIER1", 30),
    "OT_TIER2": _ot("Overtime – tier 2", "OT_RATE_TIER2", 31),
    "OT_TIER3": _ot("Overtime – tier 3", "OT_RATE_TIER3", 32),
    "OT_NIGHT": _ot("Night overtime", "OT_RATE_NIGHT", 33),
    "OT_REST_DAY": _ot("Rest day work", "OT_RATE_REST_DAY", 34),
    "OT_HOLIDAY": _ot("Public holiday work", "OT_RATE_HOLIDAY", 35),
    "ABSENCE": dict(
        name="Unpaid absence",
        kind="GROSS_DEDUCTION",
        method="QUANTITY",
        is_system=True,
        formula="BASE_FULL / ABSENCE_DAY_DIVISOR",
        prorated=False,
        payslip_order=40,
    ),
    "RESPONSIBILITY": dict(
        name="Responsibility bonus", kind="GAIN", method="FIXED", payslip_order=50
    ),
    "PERFORMANCE": dict(
        name="Performance bonus",
        kind="GAIN",
        method="FIXED",
        prorated=False,
        payslip_order=51,
    ),
    "HOUSING": dict(
        name="Housing allowance", kind="GAIN", method="FIXED", payslip_order=52
    ),
    "TRANSPORT": dict(
        name="Transport allowance",
        kind="GAIN",
        method="FIXED",
        is_taxable=False,
        is_contributory=False,
        payslip_order=53,
    ),
    "REPRESENTATION": dict(
        name="Representation allowance", kind="GAIN", method="FIXED", payslip_order=54
    ),
    "LEAVE_ALLOWANCE": dict(
        name="Leave allowance",
        kind="GAIN",
        method="FIXED",
        is_system=True,
        prorated=False,
        in_leave_allowance_base=False,
        payslip_order=60,
    ),
    "BACK_PAY": dict(
        name="Back pay",
        kind="GAIN",
        method="FIXED",
        is_system=True,
        prorated=False,
        payslip_order=61,
    ),
    "THIRTEENTH_MONTH": dict(
        name="Thirteenth month",
        kind="GAIN",
        method="FORMULA",
        formula="BASE_FULL * MONTHS_WORKED_YEAR / 12",
        periodicity="ANNUAL",
        payment_month=12,
        prorated=False,
        in_leave_allowance_base=False,
        payslip_order=62,
    ),
    "LEAVE_COMPENSATION": dict(
        name="Compensation of remaining leave",
        kind="GAIN",
        method="FIXED",
        is_system=True,
        prorated=False,
        in_leave_allowance_base=False,
        payslip_order=63,
    ),
    "NOTICE_INDEMNITY": dict(
        name="Notice indemnity",
        kind="GAIN",
        method="FIXED",
        is_system=True,
        prorated=False,
        in_leave_allowance_base=False,
        payslip_order=64,
    ),
    "SEVERANCE": dict(
        name="Severance allowance",
        kind="GAIN",
        method="FIXED",
        is_system=True,
        prorated=False,
        is_taxable=False,
        is_contributory=False,
        in_leave_allowance_base=False,
        payslip_order=65,
    ),
    "EXPENSES": dict(
        name="Expense reimbursement",
        kind="GAIN",
        method="FIXED",
        is_taxable=False,
        is_contributory=False,
        in_leave_allowance_base=False,
        prorated=False,
        payslip_order=70,
    ),
    "BIK_HOUSING": _bik("Benefit in kind – housing", "BIK_HOUSING_RATE", 80),
    "BIK_ELECTRICITY": _bik(
        "Benefit in kind – electricity", "BIK_ELECTRICITY_RATE", 81
    ),
    "BIK_WATER": _bik("Benefit in kind – water", "BIK_WATER_RATE", 82),
    "BIK_DOMESTIC": dict(
        name="Benefit in kind – domestic staff",
        kind="GAIN",
        method="FORMULA",
        formula="CASH_TAXABLE * BIK_DOMESTIC_RATE / 100 * VALUE",
        is_benefit_in_kind=True,
        in_leave_allowance_base=False,
        prorated=False,
        payslip_order=83,
    ),
    "BIK_VEHICLE": _bik("Benefit in kind – vehicle", "BIK_VEHICLE_RATE", 84),
    "BIK_FOOD": _bik("Benefit in kind – food", "BIK_FOOD_RATE", 85),
    "UNION_DUES": dict(
        name="Union dues",
        kind="NET_DEDUCTION",
        method="FIXED",
        prorated=False,
        payslip_order=920,
    ),
    "OTHER_DEDUCTION": dict(
        name="Other deduction",
        kind="NET_DEDUCTION",
        method="FIXED",
        prorated=False,
        payslip_order=930,
    ),
}


def load(apps=None):
    """Create the missing reference data (never overwrites existing rows)."""

    def model(name):
        if apps is not None:
            return apps.get_model("payroll", name)
        from django.apps import apps as global_apps

        return global_apps.get_model("payroll", name)

    Parameter, Scale = model("PayrollParameter"), model("Scale")
    Deduction, Element = model("StatutoryDeduction"), model("SalaryElement")
    for code, (name, value, unit, description) in PARAMETERS.items():
        if not Parameter.objects.filter(code=code).exists():
            Parameter.objects.create(
                code=code,
                name=name,
                value=Decimal(value),
                unit=unit,
                description=description,
                effective_from=START,
            )
    for code, (name, kind, brackets) in SCALES.items():
        if not Scale.objects.filter(code=code).exists():
            Scale.objects.create(
                code=code, name=name, kind=kind, brackets=brackets, effective_from=START
            )
    for code, fields in DEDUCTIONS.items():
        if not Deduction.objects.filter(code=code).exists():
            values = {
                k: (
                    Decimal(v)
                    if k in ("employee_rate", "employer_rate", "result_divisor")
                    else v
                )
                for k, v in fields.items()
            }
            Deduction.objects.create(code=code, effective_from=START, **values)
    for code, fields in ELEMENTS.items():
        Element.objects.get_or_create(code=code, defaults=fields)
