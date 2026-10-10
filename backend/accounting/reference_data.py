"""
Default SYSCOHADA (revised) accounts used by the payroll and their mapping.
They are loaded once and then adapted by the accountant (BN-130).
"""

import datetime

START = datetime.date(2000, 1, 1)

ACCOUNTS = {
    "421": "Personnel, avances et acomptes",
    "422": "Personnel, rémunérations dues",
    "423": "Personnel, oppositions, saisies-arrêts",
    "4282": "Dettes provisionnées pour congés à payer",
    "431": "Sécurité sociale (CNPS)",
    "4381": "Crédit Foncier du Cameroun",
    "4382": "Fonds National de l'Emploi",
    "4471": "État, impôt sur salaires (IRPP)",
    "4472": "État, centimes additionnels communaux (CAC)",
    "4473": "État, redevance audiovisuelle (RAV)",
    "4474": "Communes, taxe de développement local (TDL)",
    "5211": "Banques locales",
    "571": "Caisse",
    "6413": "Taxes sur appointements et salaires",
    "6611": "Appointements, salaires et commissions",
    "6612": "Primes et gratifications",
    "6613": "Congés payés",
    "6614": "Indemnités de préavis, de licenciement et de recherche d'embauche",
    "6617": "Avantages en nature",
    "6631": "Indemnités de logement",
    "6632": "Indemnités de représentation",
    "6634": "Indemnités de transport",
    "6638": "Autres indemnités et avantages divers",
    "6641": "Charges sociales sur rémunération du personnel national",
    "758": "Produits divers",
}

JOURNALS = {
    "PAIE": ("Journal de paie", "PAYROLL"),
    "OD": ("Opérations diverses", "MISC"),
    "BQ": ("Banque", "BANK"),
}

# (source_type, source_code): (debit, credit, employer_debit, employer_credit)
MAPPINGS = {
    ("ELEMENT", ""): ("6611", "422", None, None),
    ("ELEMENT", "SENIORITY"): ("6612", "422", None, None),
    ("ELEMENT", "RESPONSIBILITY"): ("6612", "422", None, None),
    ("ELEMENT", "PERFORMANCE"): ("6612", "422", None, None),
    ("ELEMENT", "THIRTEENTH_MONTH"): ("6612", "422", None, None),
    ("ELEMENT", "HOUSING"): ("6631", "422", None, None),
    ("ELEMENT", "REPRESENTATION"): ("6632", "422", None, None),
    ("ELEMENT", "TRANSPORT"): ("6634", "422", None, None),
    ("ELEMENT", "EXPENSES"): ("6638", "422", None, None),
    ("ELEMENT", "LEAVE_ALLOWANCE"): ("6613", "422", None, None),
    ("ELEMENT", "LEAVE_COMPENSATION"): ("6613", "422", None, None),
    ("ELEMENT", "NOTICE_INDEMNITY"): ("6614", "422", None, None),
    ("ELEMENT", "SEVERANCE"): ("6614", "422", None, None),
    # Benefits in kind are not paid in cash: counterpart in a product account.
    ("ELEMENT", "BIK_HOUSING"): ("6617", "758", None, None),
    ("ELEMENT", "BIK_ELECTRICITY"): ("6617", "758", None, None),
    ("ELEMENT", "BIK_WATER"): ("6617", "758", None, None),
    ("ELEMENT", "BIK_DOMESTIC"): ("6617", "758", None, None),
    ("ELEMENT", "BIK_VEHICLE"): ("6617", "758", None, None),
    ("ELEMENT", "BIK_FOOD"): ("6617", "758", None, None),
    ("ELEMENT", "UNION_DUES"): ("422", "423", None, None),
    ("ELEMENT", "OTHER_DEDUCTION"): ("422", "423", None, None),
    ("DEDUCTION", ""): ("422", "431", "6641", "431"),
    ("DEDUCTION", "CFC"): ("422", "4381", "6413", "4381"),
    ("DEDUCTION", "FNE"): ("422", "4382", "6413", "4382"),
    ("DEDUCTION", "IRPP"): ("422", "4471", None, None),
    ("DEDUCTION", "CAC"): ("422", "4472", None, None),
    ("DEDUCTION", "CRTV"): ("422", "4473", None, None),
    ("DEDUCTION", "TDL"): ("422", "4474", None, None),
    ("LOAN", ""): ("422", "421", None, None),
    ("THIRD_PARTY", ""): ("422", "423", None, None),
    ("NET_PAY", ""): (None, "422", None, None),
    ("BANK", ""): (None, "5211", None, None),
    ("CASH", ""): (None, "571", None, None),
    ("PROVISION", ""): ("6613", "4282", None, None),
}


def load(apps=None):
    def model(name):
        if apps is not None:
            return apps.get_model("accounting", name)
        from django.apps import apps as global_apps

        return global_apps.get_model("accounting", name)

    Account, Journal, Mapping = (
        model("Account"),
        model("Journal"),
        model("AccountMapping"),
    )
    for number, name in ACCOUNTS.items():
        Account.objects.get_or_create(number=number, defaults={"name": name})
    for code, (name, kind) in JOURNALS.items():
        Journal.objects.get_or_create(code=code, defaults={"name": name, "kind": kind})
    accounts = {a.number: a for a in Account.objects.all()}
    for (source_type, source_code), numbers in MAPPINGS.items():
        if Mapping.objects.filter(
            source_type=source_type, source_code=source_code
        ).exists():
            continue
        debit, credit, employer_debit, employer_credit = (
            accounts.get(n) if n else None for n in numbers
        )
        Mapping.objects.create(
            source_type=source_type,
            source_code=source_code,
            debit_account=debit,
            credit_account=credit,
            employer_debit_account=employer_debit,
            employer_credit_account=employer_credit,
            effective_from=START,
        )
