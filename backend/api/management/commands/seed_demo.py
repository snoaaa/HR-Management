"""
Demonstration data for every module (Cameroonian context).

Run after ``seed_data`` (which calls it at the end). It goes through the
services of the application, so that the data obeys the same rules as the
screens: contracts are validated and activated, attendance days are
computed from the clockings, leave balances are checked, payslips are
calculated by the payroll engine and validated, which posts the accounting
entries, and so on.

The command is idempotent: it stops at once when the demonstration
departments already exist.
"""

import datetime
import random
import traceback
import unicodedata
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test.utils import override_settings
from django.utils import timezone

from employees.models import EducationAndExperience, Employee, FamilyMember
from organisation.models import (
    Classification,
    CompanyIdentity,
    CostCentre,
    Department,
    Position,
    Site,
)

User = get_user_model()
PASSWORD = "password123"

SITES = [
    ("HQ01", "Douala head office", "Rue Joss, Bonanjo, Douala"),
    ("YDE01", "Yaoundé agency", "Avenue Kennedy, Centre ville, Yaoundé"),
    ("GAR01", "Garoua depot", "Quartier Roumdé Adjia, Garoua"),
    ("BAF01", "Bafoussam branch", "Route de Foumban, Bafoussam"),
]

COST_CENTRES = [
    ("CC-ADM", "Administration"),
    ("CC-FIN", "Finance"),
    ("CC-TECH", "Technology"),
    ("CC-COM", "Commercial"),
    ("CC-OPS", "Operations"),
]

# key: category, grade, echelon, coefficient, executive
CLASSIFICATIONS = {
    "W2": ("Worker", "Cat. 2", "A", 130, False),
    "W3": ("Worker", "Cat. 3", "B", 150, False),
    "E4": ("Employee", "Cat. 4", "A", 180, False),
    "E5": ("Employee", "Cat. 5", "B", 210, False),
    "S7": ("Supervisor", "Cat. 7", "A", 270, False),
    "S8": ("Supervisor", "Cat. 8", "B", 310, False),
    "X10": ("Executive", "Cat. 10", "A", 400, True),
    "X11": ("Executive", "Cat. 11", "B", 480, True),
    "X12": ("Executive", "Cat. 12", "C", 600, True),
}

# Department: code, name, cost centre, site, parent, positions
# Position: code, title, classification, headcount, salary range, head
DEPARTMENTS = [
    (
        "DG",
        "General Management",
        "CC-ADM",
        "HQ01",
        None,
        [
            ("DG01", "General Manager", "X12", 1, (2800000, 2800000), True),
            ("DG02", "Executive assistant", "E5", 1, (320000, 360000), False),
        ],
    ),
    (
        "DRH",
        "Human Resources",
        "CC-ADM",
        "HQ01",
        "DG",
        [
            ("HR01", "HR officer", "S7", 2, (420000, 480000), False),
            ("HR02", "Payroll officer", "S8", 1, (520000, 520000), False),
        ],
    ),
    (
        "DAF",
        "Finance & Accounting",
        "CC-FIN",
        "HQ01",
        "DG",
        [
            ("FIN01", "Finance manager", "X11", 1, (1450000, 1450000), True),
            ("FIN02", "Chief accountant", "X10", 1, (950000, 950000), False),
            ("FIN03", "Accountant", "S7", 2, (380000, 450000), False),
            ("FIN04", "Treasurer", "S8", 1, (500000, 500000), False),
        ],
    ),
    (
        "ENG01",
        "Engineering",
        "CC-TECH",
        "HQ01",
        "DG",
        [
            ("ENG00", "Engineering manager", "X11", 1, (1600000, 1600000), True),
            ("DEV01", "Software Developer", "S8", 3, (550000, 750000), False),
            ("QA01", "Quality assurance engineer", "S7", 2, (450000, 520000), False),
            ("OPS01", "DevOps engineer", "X10", 1, (850000, 850000), False),
        ],
    ),
    (
        "COM",
        "Sales & Marketing",
        "CC-COM",
        "YDE01",
        "DG",
        [
            ("COM01", "Sales manager", "X11", 1, (1300000, 1300000), True),
            ("COM02", "Sales representative", "E5", 5, (250000, 340000), False),
            ("COM03", "Marketing officer", "S7", 2, (400000, 460000), False),
        ],
    ),
    (
        "LOG",
        "Operations & Logistics",
        "CC-OPS",
        "GAR01",
        "DG",
        [
            ("LOG01", "Operations manager", "X10", 1, (1100000, 1100000), True),
            ("LOG02", "Logistics supervisor", "S7", 2, (380000, 420000), False),
            ("LOG03", "Warehouse operator", "W2", 6, (95000, 130000), False),
            ("LOG04", "Driver", "W3", 3, (120000, 150000), False),
        ],
    ),
    (
        "SAV",
        "Customer Service",
        "CC-COM",
        "YDE01",
        "COM",
        [
            ("SAV01", "Customer service supervisor", "S8", 1, (480000, 480000), True),
            ("SAV02", "Customer service agent", "E4", 5, (160000, 220000), False),
        ],
    ),
    (
        "IT",
        "IT Support",
        "CC-TECH",
        "BAF01",
        "ENG01",
        [
            ("IT01", "IT support lead", "S8", 1, (600000, 600000), True),
            ("IT02", "IT technician", "E5", 3, (230000, 300000), False),
        ],
    ),
]

SURNAMES = [
    "Nkoulou",
    "Mbarga",
    "Etoa",
    "Fotso",
    "Kamga",
    "Tchoupo",
    "Ndjock",
    "Abena",
    "Essomba",
    "Atangana",
    "Ngono",
    "Manga",
    "Tabi",
    "Ayuk",
    "Ndifor",
    "Nfor",
    "Mbida",
    "Owona",
    "Onana",
    "Djoumessi",
    "Kenfack",
    "Talla",
    "Nana",
    "Wamba",
    "Moukoko",
    "Ekambi",
    "Ebongue",
    "Ngassa",
    "Simo",
    "Tchinda",
    "Yimga",
    "Hamadou",
    "Bello",
    "Oumarou",
    "Abdoulaye",
    "Ngwa",
    "Achu",
    "Nkeng",
    "Fru",
    "Ebai",
    "Enow",
    "Tanyi",
    "Ashu",
    "Besong",
    "Mvondo",
    "Ndzana",
    "Belinga",
    "Zambo",
    "Eyenga",
    "Ngo Bassa",
]
MALE_NAMES = [
    "Jean-Paul",
    "Serge",
    "Hervé",
    "Patrick",
    "Alain",
    "Christian",
    "Emmanuel",
    "Blaise",
    "Landry",
    "Arnaud",
    "Boris",
    "Franck",
    "Ibrahim",
    "Issa",
    "Divine",
    "Clinton",
    "Desmond",
    "Ernest",
    "Martial",
    "Rodrigue",
]
FEMALE_NAMES = [
    "Marie-Claire",
    "Brigitte",
    "Sandrine",
    "Nadège",
    "Carine",
    "Estelle",
    "Pauline",
    "Aïcha",
    "Mariama",
    "Grace",
    "Prudence",
    "Mirabelle",
    "Linda",
    "Vanessa",
    "Cynthia",
    "Rose",
    "Josiane",
    "Laure",
]
CITIES = [
    ("Douala", "LITTORAL"),
    ("Yaoundé", "CENTRE"),
    ("Garoua", "NORTH"),
    ("Bafoussam", "WEST"),
    ("Bamenda", "NORTH_WEST"),
    ("Buea", "SOUTH_WEST"),
    ("Ngaoundéré", "ADAMAWA"),
    ("Bertoua", "EAST"),
    ("Ebolowa", "SOUTH"),
    ("Maroua", "FAR_NORTH"),
]
DISTRICTS = {
    "Douala": ["Akwa", "Bonapriso", "Makepe", "Bonamoussadi", "Logbessou", "Deido"],
    "Yaoundé": ["Bastos", "Essos", "Mvan", "Biyem-Assi", "Nlongkak", "Odza"],
}
BANKS = [
    ("Afriland First Bank", "10005"),
    ("Société Générale Cameroun", "10003"),
    ("BICEC", "10001"),
    ("Ecobank Cameroun", "10029"),
    ("UBA Cameroon", "10033"),
    ("CCA Bank", "10039"),
]
SCHOOLS = [
    "Université de Yaoundé I",
    "Université de Douala",
    "University of Buea",
    "ESSEC Douala",
    "École Nationale Supérieure Polytechnique",
    "IUT de Douala",
    "Université de Dschang",
    "Catholic University of Central Africa",
]
EMPLOYERS = [
    "Orange Cameroun",
    "MTN Cameroon",
    "Brasseries du Cameroun",
    "SABC",
    "Dangote Cement Cameroon",
    "Camtel",
    "Express Union",
    "Cimencam",
]
SKILLS = [
    ("Python programming", "Technical"),
    ("React / TypeScript", "Technical"),
    ("Network administration", "Technical"),
    ("SYSCOHADA accounting", "Finance"),
    ("Cameroon payroll and CNPS", "HR"),
    ("Labour law (Cameroon)", "HR"),
    ("Negotiation", "Commercial"),
    ("Customer relationship", "Commercial"),
    ("Forklift driving", "Operations"),
    ("Stock management", "Operations"),
    ("Occupational health and safety", "Operations"),
    ("Leadership", "Management"),
    ("Project management", "Management"),
    ("English (professional)", "Languages"),
    ("French (professional)", "Languages"),
    ("Excel (advanced)", "Office"),
]
SKILLS_BY_DEPARTMENT = {
    "DG": ["Leadership", "Project management", "English (professional)"],
    "DRH": ["Cameroon payroll and CNPS", "Labour law (Cameroon)", "Excel (advanced)"],
    "DAF": ["SYSCOHADA accounting", "Excel (advanced)"],
    "ENG01": ["Python programming", "React / TypeScript", "Project management"],
    "COM": ["Negotiation", "Customer relationship", "English (professional)"],
    "LOG": ["Forklift driving", "Stock management", "Occupational health and safety"],
    "SAV": ["Customer relationship", "French (professional)"],
    "IT": ["Network administration", "Python programming"],
}


def ascii_slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(c for c in text.lower() if c.isalnum())


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    last = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return datetime.date(year, month, min(day.day, last[month - 1]))


def month_start(day, offset=0):
    return add_months(day.replace(day=1), offset)


class Command(BaseCommand):
    help = "Seed demonstration data for every module (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed", type=int, default=2026, help="Random seed (reproducible data)."
        )
        parser.add_argument(
            "--only",
            default="",
            help=(
                "Comma-separated steps to (re)run on an already seeded database, "
                "e.g. --only payroll,budgets."
            ),
        )

    def handle(self, *args, **options):
        # The notifications are kept in the application, not sent by e-mail.
        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
        ):
            self._handle(options)

    def _handle(self, options):
        only = {s.strip() for s in options["only"].split(",") if s.strip()}
        if Department.objects.filter(code="LOG").exists() and not only:
            self.stdout.write("Demonstration data already present: nothing to do.")
            return
        self.rng = random.Random(options["seed"])
        self.today = timezone.now().date()
        self.admin = User.objects.filter(role="SYSTEM_ADMINISTRATOR").first()
        self.hr = User.objects.filter(role="HR_MANAGER").first() or self.admin
        self.payroll_user = (
            User.objects.filter(role="PAYROLL_OFFICER").first() or self.admin
        )
        self.used_names = set(
            Employee.objects.values_list("surname", "given_names").distinct()
        )
        self.report = []
        steps = [
            ("organisation", "Organisation", self.seed_organisation),
            ("employees", "Employees and contracts", self.seed_employees),
            ("payroll_setup", "Salary elements and loans", self.seed_payroll_setup),
            ("skills", "Skills", self.seed_skills),
            ("careers", "Career acts", self.seed_careers),
            ("leave", "Leave", self.seed_leave),
            ("attendance", "Attendance", self.seed_attendance),
            ("payroll", "Payroll and accounting", self.seed_payroll),
            ("budgets", "Budgets", self.seed_budgets),
            ("planning", "Planning", self.seed_planning),
            ("training", "Training", self.seed_training),
            ("recruitment", "Recruitment", self.seed_recruitment),
            ("evaluation", "Evaluation", self.seed_evaluation),
            ("documents", "Documents and requests", self.seed_documents),
        ]
        if only:
            unknown = only - {code for code, *_ in steps}
            if unknown:
                raise CommandError(f"Unknown step(s): {', '.join(sorted(unknown))}.")
            self._load_existing()
            steps = [step for step in steps if step[0] in only]
        for _, label, step in steps:
            self.stdout.write(f"Seeding {label.lower()}...")
            try:
                with transaction.atomic():
                    result = step()
                self.report.append(f"  {label}: {result}")
            except Exception as exc:  # keep seeding the other modules
                if options["verbosity"] > 1:
                    traceback.print_exc()
                self.report.append(f"  {label}: FAILED ({exc})")
                self.stdout.write(self.style.WARNING(f"  {label} failed: {exc}"))
        self.stdout.write(self.style.SUCCESS("Demonstration data:"))
        for line in self.report:
            self.stdout.write(line)

    def _load_existing(self):
        """Context of an already seeded database (to re-run some steps)."""
        self.sites = {s.code: s for s in Site.objects.all()}
        self.centres = {c.code: c for c in CostCentre.objects.all()}
        self.classifications = {
            key: Classification.objects.filter(
                category=category, grade=grade, echelon=echelon
            ).first()
            for key, (category, grade, echelon, *_) in CLASSIFICATIONS.items()
        }
        self.departments = {
            code: Department.objects.get(code=code)
            for code, *_ in DEPARTMENTS
            if Department.objects.filter(code=code).exists()
        }
        self.positions = {p.code: p for p in Position.objects.all()}
        self.by_department, self.heads = {}, {}
        for code, department in self.departments.items():
            team = list(
                Employee.objects.filter(
                    department=department, status="ACTIVE"
                ).order_by("id")
            )
            self.by_department[code] = team
            head = next(
                (e for e in team if e.user_id and e.user_id == department.manager_id),
                None,
            )
            if head is not None:
                self.heads[code] = head
        self.skills = {}

    # ------------------------------------------------------------------
    # Organisation
    # ------------------------------------------------------------------

    def seed_organisation(self):
        company = CompanyIdentity.objects.first()
        identity = {
            "corporate_name": "Saint Jean Services SA",
            "legal_form": "Société Anonyme (SA)",
            "registration_number": "RC/DLA/2015/B/1234",
            "tax_id": "M041500012345K",
            "social_insurance_number": "345-1234567-K",
            "address": "Rue Joss, Bonanjo",
            "city": "Douala",
            "postal_box": "4321",
            "phone": "+237 233 42 00 00",
            "email": "contact@saintjean-services.cm",
            "website": "www.saintjean-services.cm",
            "legal_representative": "Jean-Paul Mbarga",
            "legal_representative_title": "General Manager",
        }
        if company is None:
            company = CompanyIdentity.objects.create(**identity)
        elif "Silicon Valley" in (company.address or ""):
            # Untouched identity of the base seed: replace it.
            for field, value in identity.items():
                setattr(company, field, value)
            company.save()
        else:
            for field, value in identity.items():
                if not getattr(company, field):
                    setattr(company, field, value)
            company.save()

        self.sites = {}
        for code, name, address in SITES:
            site, _ = Site.objects.get_or_create(
                code=code, defaults={"name": name, "address": address}
            )
            if "Silicon Valley" in (site.address or ""):
                site.name, site.address = name, address
                site.save()
            self.sites[code] = site
        self.centres = {
            code: CostCentre.objects.get_or_create(code=code, defaults={"name": name})[
                0
            ]
            for code, name in COST_CENTRES
        }
        self.classifications = {
            key: Classification.objects.get_or_create(
                category=category,
                grade=grade,
                echelon=echelon,
                defaults={"coefficient": coefficient, "is_executive": executive},
            )[0]
            for key, (category, grade, echelon, coefficient, executive) in (
                CLASSIFICATIONS.items()
            )
        }
        self.departments, self.positions = {}, {}
        for code, name, centre, site, parent, positions in DEPARTMENTS:
            department, _ = Department.objects.get_or_create(
                code=code, defaults={"name": name, "unit_type": "DEPARTMENT"}
            )
            department.name = name
            department.site = self.sites[site]
            department.cost_centre = self.centres[centre]
            department.parent = self.departments.get(parent)
            if code == "DRH" and department.manager_id is None:
                department.manager = self.hr
            department.save()
            self.departments[code] = department
            previous = None
            for p_code, title, cls, *_ in positions:
                position, _ = Position.objects.get_or_create(
                    code=p_code, defaults={"title": title}
                )
                position.classification = self.classifications[cls]
                if not position.mission:
                    position.mission = f"{title} within the {name} department."
                position.reporting_position = previous
                position.save()
                previous = previous or position
                self.positions[p_code] = position
        return (
            f"company, {len(self.sites)} sites, {len(self.centres)} cost centres, "
            f"{len(self.departments)} departments, {len(self.positions)} positions"
        )

    # ------------------------------------------------------------------
    # Employees, users, family, education, contracts
    # ------------------------------------------------------------------

    def _name(self, sex):
        for _ in range(200):
            surname = self.rng.choice(SURNAMES)
            given = self.rng.choice(MALE_NAMES if sex == "M" else FEMALE_NAMES)
            if (surname, given) not in self.used_names:
                self.used_names.add((surname, given))
                return surname, given
        return self.rng.choice(SURNAMES), f"{given} {len(self.used_names)}"

    def _user(self, surname, given, role, email):
        base = f"{ascii_slug(given.split('-')[0])}.{ascii_slug(surname)}"
        username, index = base, 1
        while User.objects.filter(username=username).exists():
            index += 1
            username = f"{base}{index}"
        user = User(
            username=username,
            email=email,
            role=role,
            first_name=given,
            last_name=surname,
        )
        user.set_password(PASSWORD)
        user.save()
        return user

    def _hire_date(self, head):
        if head:
            start = self.today.replace(year=self.today.year - 12)
            end = self.today.replace(year=self.today.year - 3)
        else:
            start = self.today.replace(year=self.today.year - 10)
            end = add_months(self.today, -4)
        day = start + datetime.timedelta(days=self.rng.randint(0, (end - start).days))
        return day

    def _employee(self, department, position, cls_key, head, sex=None, user=None):
        sex = sex or self.rng.choice("MF")
        if user is not None and user.last_name and user.first_name:
            surname, given = user.last_name, user.first_name
            self.used_names.add((surname, given))
        else:
            surname, given = self._name(sex)
        city, region = self.rng.choice(
            CITIES[:4] if self.rng.random() < 0.8 else CITIES
        )
        birth_year = self.today.year - self.rng.randint(23, 58 if head else 50)
        birth = datetime.date(
            birth_year, self.rng.randint(1, 12), self.rng.randint(1, 28)
        )
        hire = self._hire_date(head)
        hire = max(hire, birth.replace(year=birth.year + 20))
        married = self.rng.random() < 0.55
        bank, bank_code = self.rng.choice(BANKS)
        slug = f"{ascii_slug(given.split('-')[0])}.{ascii_slug(surname)}"
        district = self.rng.choice(DISTRICTS.get(city, ["Centre"]))
        employee = Employee.objects.create(
            user=user,
            title=("MR" if sex == "M" else ("MRS" if married else "MS")),
            surname=surname,
            given_names=given,
            maiden_name=(self.rng.choice(SURNAMES) if sex == "F" and married else ""),
            date_of_birth=birth,
            place_of_birth=self.rng.choice(CITIES)[0],
            sex=sex,
            nationality="Cameroonian" if self.rng.random() < 0.95 else "Gabonese",
            marital_status=(
                "MARRIED"
                if married
                else self.rng.choice(["SINGLE", "SINGLE", "DIVORCED"])
            ),
            identity_document_type="National identity card",
            identity_document_number=f"{self.rng.randint(100000000, 999999999)}",
            identity_document_issue_date=add_months(
                self.today, -self.rng.randint(6, 100)
            ),
            identity_document_issue_place=city,
            identity_document_validity=add_months(
                self.today, self.rng.randint(-2, 110)
            ),
            blood_group=self.rng.choice(["O+", "O+", "A+", "B+", "AB+", "O-", "A-"]),
            education_level=(
                self.rng.choice(["MASTER", "DOCTORATE"])
                if head
                else self.rng.choice(
                    ["BEPC", "PROBATOIRE", "BAC"]
                    if cls_key.startswith("W")
                    else ["BAC", "BTS", "LICENCE", "MASTER"]
                )
            ),
            spoken_languages=self.rng.choice(
                ["French, English", "French", "English, French", "French, Fulfulde"]
            ),
            address=f"{district}, {city}",
            city=city,
            region=region,
            postal_box=(
                str(self.rng.randint(100, 15000)) if self.rng.random() < 0.4 else ""
            ),
            phone_number=f"+237 6{self.rng.choice('5789')}{self.rng.randint(1000000, 9999999)}",
            professional_phone=(
                f"+237 233 4{self.rng.randint(10, 99)} {self.rng.randint(100, 999)}"
                if head or cls_key.startswith(("S", "X"))
                else ""
            ),
            personal_email=f"{slug}@gmail.com",
            professional_email=f"{slug}@saintjean-services.cm",
            emergency_contact_name=f"{self.rng.choice(FEMALE_NAMES + MALE_NAMES)} {surname}",
            emergency_contact_number=f"+237 69{self.rng.randint(1000000, 9999999)}",
            emergency_contact_relationship=(
                "Spouse"
                if married
                else self.rng.choice(["Mother", "Father", "Brother", "Sister"])
            ),
            social_insurance_number=f"{self.rng.randint(100, 999)}-{self.rng.randint(1000000, 9999999)}-{self.rng.choice('ABCDEFGHK')}",
            cnps_registration_date=hire
            + datetime.timedelta(days=self.rng.randint(5, 40)),
            tax_identification_number=f"P0{self.rng.randint(10, 99)}{self.rng.randint(1000000, 9999999)}{self.rng.choice('ABCDKMNP')}",
            bank_name=bank,
            bank_branch=f"Agence {city}",
            account_number=f"{bank_code}-{self.rng.randint(10000, 99999)}-{self.rng.randint(10000000000, 99999999999)}",
            bank_key=f"{self.rng.randint(10, 97)}",
            method_of_payment=(
                "TRANSFER"
                if not cls_key.startswith("W") or self.rng.random() < 0.6
                else "CASH"
            ),
            department=department,
            position=position,
            classification=self.classifications[cls_key],
            contract_type="PERMANENT",
            date_of_hire=hire,
            workplace=department.site,
            has_disability=self.rng.random() < 0.03,
        )
        if married:
            FamilyMember.objects.create(
                employee=employee,
                name=f"{self.rng.choice(FEMALE_NAMES if sex == 'M' else MALE_NAMES)} {surname}",
                date_of_birth=birth.replace(year=birth.year + self.rng.randint(-5, 4)),
                relationship="SPOUSE",
            )
        for _ in range(
            self.rng.choice([0, 1, 1, 2, 2, 3, 4])
            if birth_year < self.today.year - 26
            else 0
        ):
            child_birth = datetime.date(
                self.rng.randint(birth_year + 22, self.today.year - 1),
                self.rng.randint(1, 12),
                self.rng.randint(1, 28),
            )
            FamilyMember.objects.create(
                employee=employee,
                name=f"{self.rng.choice(MALE_NAMES + FEMALE_NAMES)} {surname}",
                date_of_birth=child_birth,
                relationship="CHILD",
            )
        graduation = birth.year + self.rng.randint(21, 26)
        EducationAndExperience.objects.create(
            employee=employee,
            entry_type="EDUCATION",
            title={
                "DOCTORATE": "PhD",
                "MASTER": "Master's degree",
                "LICENCE": "Bachelor's degree",
                "BTS": "BTS / HND",
                "BAC": "Baccalauréat",
                "PROBATOIRE": "Probatoire",
                "BEPC": "BEPC",
            }.get(employee.education_level, "Diploma"),
            institution_or_company=self.rng.choice(SCHOOLS),
            start_date=datetime.date(graduation - 3, 9, 1),
            end_date=datetime.date(graduation, 7, 15),
        )
        if hire.year - graduation > 2:
            EducationAndExperience.objects.create(
                employee=employee,
                entry_type="EXPERIENCE",
                title=position.title,
                institution_or_company=self.rng.choice(EMPLOYERS),
                start_date=datetime.date(graduation, 10, 1),
                end_date=hire - datetime.timedelta(days=30),
            )
        return employee

    def _contract(
        self, employee, salary, kind="PERMANENT", start=None, end=None, trial_end=None
    ):
        from contracts.models import Contract
        from contracts.services import activate

        contract = Contract.objects.create(
            employee=employee,
            contract_type=kind,
            start_date=start or employee.date_of_hire,
            end_date=end,
            trial_period_end=trial_end,
            base_salary=Decimal(salary),
            weekly_hours=Decimal("40"),
            workplace=employee.workplace,
            department=employee.department,
            position=employee.position,
            classification=employee.classification,
            created_by=self.hr,
        )
        activate(contract, self.hr)
        return contract

    def seed_employees(self):
        self.heads = {}
        self.by_department = {}
        linked = {
            "HR02": User.objects.filter(
                role="PAYROLL_OFFICER", employee_profile__isnull=True
            ).first(),
            "FIN02": User.objects.filter(
                role="ACCOUNTANT", employee_profile__isnull=True
            ).first(),
        }
        created = fixed_term = users = 0
        for code, name, _, _, _, positions in DEPARTMENTS:
            department = self.departments[code]
            for p_code, title, cls_key, count, (low, high), head in positions:
                position = self.positions[p_code]
                for index in range(count):
                    existing = Employee.objects.filter(position=position).count()
                    if p_code == "DEV01" and existing >= count + 2:
                        break
                    user = linked.pop(p_code, None) if index == 0 else None
                    sex = self.rng.choice("MF")
                    if user is not None:
                        # Existing demo account (payroll, accountant): give it a real name.
                        user.last_name, user.first_name = self._name(sex)
                        user.save(update_fields=["first_name", "last_name"])
                    role = None
                    if head:
                        role = (
                            "GENERAL_MANAGEMENT"
                            if code == "DG"
                            else "HEAD_OF_DEPARTMENT"
                        )
                    elif p_code == "HR01" and user is None:
                        role = "HR_OFFICER"
                    elif self.rng.random() < 0.45:
                        role = "EMPLOYEE"
                    if user is None and role:
                        surname, given = self._name(sex)
                        user = self._user(
                            surname,
                            given,
                            role,
                            f"{ascii_slug(given)}.{ascii_slug(surname)}@saintjean-services.cm",
                        )
                        users += 1
                    employee = self._employee(
                        department, position, cls_key, head, sex, user
                    )
                    salary = (
                        self.rng.randrange(low, high + 1, 5000) if high > low else low
                    )
                    recent = (self.today - employee.date_of_hire).days < 600
                    if not head and recent and self.rng.random() < 0.6:
                        # Fixed-term contract (art. 25: 2 years maximum).
                        employee.contract_type = "FIXED_TERM"
                        employee.save(update_fields=["contract_type"])
                        self._contract(
                            employee,
                            salary,
                            "FIXED_TERM",
                            end=add_months(employee.date_of_hire, 24)
                            - datetime.timedelta(days=1),
                        )
                        fixed_term += 1
                    else:
                        self._contract(employee, salary)
                    if head:
                        self.heads[code] = employee
                        department.manager = employee.user
                        department.save(update_fields=["manager"])
                    self.by_department.setdefault(code, []).append(employee)
                    created += 1
        # Contracts close to their term (deadline alerts) and new hires on trial.
        expiring = self._new_hire(
            "SAV", "SAV02", "E4", 175000, months_ago=23, kind="FIXED_TERM"
        )
        trial = self._new_hire("ENG01", "QA01", "S7", 470000, months_ago=2)
        self._new_hire("LOG", "LOG03", "W2", 98000, months_ago=1, kind="FIXED_TERM")
        created += 3
        # Base seed employees join the demo organisation.
        for employee in Employee.objects.filter(
            department__code="ENG01", position__code="DEV01"
        ):
            self.by_department.setdefault("ENG01", [])
            if employee not in self.by_department["ENG01"]:
                self.by_department["ENG01"].append(employee)
        elie = Employee.objects.filter(user=self.hr).first()
        if elie is not None:
            if elie.department_id is None or elie.department.code != "DRH":
                elie.department = self.departments["DRH"]
                elie.save(update_fields=["department"])
            self.heads["DRH"] = elie
            self.by_department.setdefault("DRH", []).insert(0, elie)
        return (
            f"{created} employees ({fixed_term + 2} fixed-term), {users} user accounts, "
            f"contracts expiring for {expiring.full_name}, trial for {trial.full_name}"
        )

    def _new_hire(self, dept, p_code, cls_key, salary, months_ago, kind="PERMANENT"):
        department = self.departments[dept]
        employee = self._employee(department, self.positions[p_code], cls_key, False)
        employee.date_of_hire = add_months(self.today, -months_ago).replace(day=1)
        employee.contract_type = kind
        employee.cnps_registration_date = employee.date_of_hire + datetime.timedelta(
            days=10
        )
        employee.save()
        start = employee.date_of_hire
        if kind == "FIXED_TERM":
            end = add_months(start, 24) - datetime.timedelta(days=1)
            end = min(end, self.today + datetime.timedelta(days=25))
            self._contract(employee, salary, kind, start=start, end=end)
        else:
            self._contract(
                employee, salary, start=start, trial_end=add_months(start, 3)
            )
        self.by_department.setdefault(dept, []).append(employee)
        return employee

    # ------------------------------------------------------------------
    # Payroll set-up: element values, loans, third-party deductions
    # ------------------------------------------------------------------

    def seed_payroll_setup(self):
        from payroll.models import ElementValue, Loan, SalaryElement

        elements = {e.code: e for e in SalaryElement.objects.all()}
        since = datetime.date(self.today.year - 5, 1, 1)
        values = 0
        transport = {
            "Worker": 20000,
            "Employee": 25000,
            "Supervisor": 35000,
            "Executive": 50000,
        }
        housing = {"Supervisor": 60000, "Executive": 150000}
        for cls in self.classifications.values():
            for code, table in (("TRANSPORT", transport), ("HOUSING", housing)):
                if code in elements and cls.category in table:
                    ElementValue.objects.get_or_create(
                        element=elements[code],
                        classification=cls,
                        effective_from=since,
                        defaults={"value": Decimal(table[cls.category])},
                    )
                    values += 1
        for code, head in self.heads.items():
            if "RESPONSIBILITY" in elements:
                ElementValue.objects.create(
                    element=elements["RESPONSIBILITY"],
                    employee=head,
                    value=Decimal(200000 if code == "DG" else 100000),
                    effective_from=head.date_of_hire,
                    comment="Head of department",
                )
                values += 1
        if "REPRESENTATION" in elements and "DG" in self.heads:
            ElementValue.objects.create(
                element=elements["REPRESENTATION"],
                employee=self.heads["DG"],
                value=Decimal(250000),
                effective_from=self.heads["DG"].date_of_hire,
            )
            values += 1
        first = month_start(self.today, -3)
        loans = 0
        from contracts.services import active_contract

        # Only employees who can repay: the instalment stays below a third of
        # the base salary (part of the salary that can be withheld).
        candidates = []
        for team in self.by_department.values():
            for employee in team:
                contract = active_contract(employee)
                if contract and contract.base_salary >= 250000:
                    candidates.append((employee, contract.base_salary))
        for employee, salary in self.rng.sample(candidates, min(6, len(candidates))):
            months = self.rng.choice([3, 6, 10])
            amount = Decimal(self.rng.choice([150000, 300000, 500000, 750000]))
            amount = min(amount, (salary / 3 * months).quantize(Decimal("1000")))
            Loan.objects.create(
                employee=employee,
                kind="ADVANCE" if months == 3 else "LOAN",
                amount=amount,
                installment=(amount / months).quantize(Decimal("1")),
                granted_on=first - datetime.timedelta(days=10),
                first_year=first.year,
                first_month=first.month,
                comment="School fees" if months == 3 else "Personal loan",
                created_by=self.payroll_user,
            )
            loans += 1
        return f"{values} element values (transport, housing, responsibility), {loans} loans"

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def seed_skills(self):
        from training.models import EmployeeSkill, PositionSkill, Skill

        skills = {
            name: Skill.objects.get_or_create(
                name=name, defaults={"category": category}
            )[0]
            for name, category in SKILLS
        }
        position_links = employee_links = 0
        for code, *_, positions in DEPARTMENTS:
            for p_code, *_ in positions:
                for name in SKILLS_BY_DEPARTMENT.get(code, []):
                    PositionSkill.objects.get_or_create(
                        position=self.positions[p_code],
                        skill=skills[name],
                        defaults={"required_level": self.rng.choice([2, 3, 3, 4])},
                    )
                    position_links += 1
            for employee in self.by_department.get(code, []):
                for name in SKILLS_BY_DEPARTMENT.get(code, []):
                    EmployeeSkill.objects.get_or_create(
                        employee=employee,
                        skill=skills[name],
                        defaults={
                            "level": self.rng.randint(1, 5),
                            "assessed_at": add_months(
                                self.today, -self.rng.randint(1, 18)
                            ),
                            "source": "Annual evaluation",
                        },
                    )
                    employee_links += 1
        self.skills = skills
        return f"{len(skills)} skills, {position_links} required, {employee_links} assessed"

    # ------------------------------------------------------------------
    # Careers
    # ------------------------------------------------------------------

    def seed_careers(self):
        from careers import services
        from careers.models import CareerAct

        acts = 0
        # A promotion already applied (before the payroll months).
        sales = min(self.by_department["COM"][1:], key=lambda e: e.date_of_hire)
        act = CareerAct.objects.create(
            employee=sales,
            act_type="PROMOTION",
            effective_date=max(
                month_start(self.today, -5), month_start(sales.date_of_hire, 1)
            ),
            reason="Best sales results of the year.",
            new_classification=self.classifications["S7"],
            new_base_salary=Decimal(420000),
            created_by=self.hr,
        )
        act.status = "APPROVED"
        act.save(update_fields=["status"])
        services.apply(act, self.hr)
        acts += 1
        # A salary revision waiting for approval.
        developer = self.by_department["ENG01"][1]
        act = CareerAct.objects.create(
            employee=developer,
            act_type="SALARY_REVISION",
            effective_date=month_start(self.today, 1),
            reason="Annual review: objectives exceeded.",
            increase_percent=Decimal("8"),
            created_by=self.hr,
        )
        services.submit(act, self.hr)
        acts += 1
        # A transfer to the Yaoundé agency, approved for next month.
        operator = self.by_department["LOG"][-2]
        CareerAct.objects.create(
            employee=operator,
            act_type="TRANSFER",
            status="APPROVED",
            effective_date=month_start(self.today, 1),
            reason="Opening of the Yaoundé storage area.",
            new_workplace=self.sites["YDE01"],
            created_by=self.hr,
        )
        acts += 1
        # A written warning.
        agent = self.by_department["SAV"][-1]
        act = CareerAct.objects.create(
            employee=agent,
            act_type="DISCIPLINARY",
            effective_date=self.today - datetime.timedelta(days=12),
            reason="Repeated unjustified late arrivals.",
            disciplinary_measure="WARNING",
            created_by=self.hr,
        )
        services.submit(act, self.hr)
        acts += 1
        # An acting position (temporary) for a supervisor.
        supervisor = self.by_department["LOG"][1]
        CareerAct.objects.create(
            employee=supervisor,
            act_type="ACTING",
            status="DRAFT",
            effective_date=month_start(self.today, 1),
            end_date=add_months(month_start(self.today, 1), 3)
            - datetime.timedelta(days=1),
            reason="Acting operations manager during the manager's leave.",
            new_position=self.positions["LOG01"],
            created_by=self.hr,
        )
        acts += 1
        return f"{acts} career acts (applied, pending, approved, draft)"

    # ------------------------------------------------------------------
    # Leave
    # ------------------------------------------------------------------

    def _leave(self, employee, code, start, days, status, reason=""):
        from leave import services
        from leave.models import LeaveRequest, LeaveType

        leave_type = LeaveType.objects.get(code=code)
        end = start
        counted = 1
        while counted < days:
            end += datetime.timedelta(days=1)
            if end.weekday() < 6:
                counted += 1
        request = LeaveRequest(
            employee=employee,
            leave_type=leave_type,
            start_date=start,
            end_date=end,
            reason=reason,
            created_by=employee.user or self.hr,
        )
        try:
            if status == "SUBMITTED":
                services.submit(request, employee.user or self.hr)
            else:
                services.prepare(request)
                request.status = "SUBMITTED"
                request.submitted_at = timezone.now()
                request.save()
                if status == "APPROVED":
                    services.approve(request, self.hr)
                else:
                    request.status = status
                    request.decided_at = timezone.now()
                    request.save()
        except services.LeaveError:
            return None
        return request

    def _next_weekday(self, day):
        while day.weekday() >= 5:
            day += datetime.timedelta(days=1)
        return day

    def seed_leave(self):
        population = [e for team in self.by_department.values() for e in team]
        self.rng.shuffle(population)
        self.on_leave = set()
        count = {"APPROVED": 0, "SUBMITTED": 0, "REFUSED": 0}
        last_month = month_start(self.today, -1)
        for employee in population[:8]:
            start = self._next_weekday(
                last_month + datetime.timedelta(days=self.rng.randint(0, 18))
            )
            if self._leave(
                employee,
                "ANNUAL",
                start,
                self.rng.randint(5, 12),
                "APPROVED",
                "Annual holidays",
            ):
                count["APPROVED"] += 1
        for employee in population[8:12]:
            start = self._next_weekday(
                month_start(self.today, -2)
                + datetime.timedelta(days=self.rng.randint(0, 15))
            )
            if self._leave(
                employee,
                "ANNUAL",
                start,
                self.rng.randint(6, 15),
                "APPROVED",
                "Family holidays",
            ):
                count["APPROVED"] += 1
        for employee in population[12:18]:
            start = self._next_weekday(
                month_start(self.today, 1)
                + datetime.timedelta(days=self.rng.randint(0, 20))
            )
            if self._leave(
                employee,
                "ANNUAL",
                start,
                self.rng.randint(5, 10),
                "SUBMITTED",
                "End of year holidays",
            ):
                count["SUBMITTED"] += 1
        for employee in population[18:21]:
            start = self._next_weekday(
                month_start(self.today, 2)
                + datetime.timedelta(days=self.rng.randint(5, 15))
            )
            if self._leave(
                employee,
                "ANNUAL",
                start,
                self.rng.randint(8, 15),
                "APPROVED",
                "Christmas holidays",
            ):
                count["APPROVED"] += 1
        for employee in population[21:23]:
            start = self._next_weekday(
                self.today + datetime.timedelta(days=self.rng.randint(3, 10))
            )
            if self._leave(employee, "ANNUAL", start, 4, "REFUSED", "Personal reasons"):
                count["REFUSED"] += 1
        unpaid = population[23]
        start = self._next_weekday(last_month + datetime.timedelta(days=20))
        if self._leave(unpaid, "UNPAID", start, 2, "APPROVED", "Personal business"):
            count["APPROVED"] += 1
        return (
            ", ".join(f"{n} {s.lower()}" for s, n in count.items()) + " leave requests"
        )

    # ------------------------------------------------------------------
    # Attendance: clockings of the previous and current months
    # ------------------------------------------------------------------

    def seed_attendance(self):
        from attendance import services
        from attendance.models import Clocking, DailyAttendance, Mission
        from leave.services import leave_on

        start = month_start(self.today, -1)
        end = self.today - datetime.timedelta(days=1)
        clockings = 0
        employees = list(
            Employee.objects.filter(status="ACTIVE").select_related("workplace")
        )
        for employee in employees:
            day = max(start, employee.date_of_hire)
            late_prone = self.rng.random() < 0.15
            batch = []
            while day <= end:
                if services.is_working_day(day, employee.workplace) and not leave_on(
                    employee, day
                ):
                    if self.rng.random() > 0.025:  # a few unjustified absences
                        # Punctual days: arrival 08:00-08:04 (within the
                        # lateness tolerance), departure at 17:00. Some
                        # employees are often late; some days have overtime.
                        minute_in = (
                            self.rng.choice([0, 2, 10, 20, 35])
                            if late_prone
                            else self.rng.randint(0, 4)
                        )
                        time_in = (
                            datetime.datetime.combine(day, datetime.time(8, 0))
                            + datetime.timedelta(minutes=minute_in)
                        ).time()
                        extra = self.rng.choice([0] * 14 + [60, 90, 120])
                        time_out = (
                            datetime.datetime.combine(day, datetime.time(17, 0))
                            + datetime.timedelta(minutes=extra)
                        ).time()
                        batch.append(
                            Clocking(
                                employee=employee,
                                date=day,
                                time_in=time_in,
                                time_out=time_out,
                                source=self.rng.choice(
                                    ["IMPORT", "IMPORT", "SELF", "MANUAL"]
                                ),
                                created_by=self.admin,
                            )
                        )
                day += datetime.timedelta(days=1)
            Clocking.objects.bulk_create(batch)
            clockings += len(batch)
        # Today: the morning clockings, still open.
        if services.is_working_day(self.today):
            for employee in employees[: len(employees) // 2]:
                if not leave_on(employee, self.today):
                    Clocking.objects.create(
                        employee=employee,
                        date=self.today,
                        time_in=datetime.time(7, self.rng.randint(40, 59)),
                        source="IMPORT",
                        created_by=self.admin,
                    )
        for employee in employees:
            services.recompute(employee, max(start, employee.date_of_hire), end)
        # Missions.
        missions = 0
        for employee in self.rng.sample(employees, min(4, len(employees))):
            begin = self._next_weekday(
                start + datetime.timedelta(days=self.rng.randint(0, 20))
            )
            Mission.objects.create(
                employee=employee,
                start_date=begin,
                end_date=begin + datetime.timedelta(days=self.rng.randint(1, 4)),
                place=self.rng.choice(
                    ["Kribi", "Limbé", "Ngaoundéré", "Bertoua", "Ebolowa"]
                ),
                purpose=self.rng.choice(
                    [
                        "Customer visit",
                        "Installation",
                        "Audit of the depot",
                        "Trade fair",
                    ]
                ),
                created_by=self.hr,
            )
            missions += 1
        # Overtime of last month approved by the managers, this month pending.
        approved = DailyAttendance.objects.filter(
            date__lt=month_start(self.today), overtime_status="PENDING"
        ).update(overtime_status="APPROVED", overtime_decided_by=self.hr)
        services.consolidate_period(start.year, start.month, self.hr)
        days = DailyAttendance.objects.count()
        return f"{clockings} clockings, {days} computed days, {approved} overtime approvals, {missions} missions"

    # ------------------------------------------------------------------
    # Payroll (3 months) and accounting
    # ------------------------------------------------------------------

    def seed_payroll(self):
        from accounting import services as accounting
        from payroll import services
        from payroll.models import SalaryElement, VariableInput

        done = []
        for offset in (-3, -2, -1):
            first = month_start(self.today, offset)
            period = services.open_period(first.year, first.month, self.payroll_user)
            if period.is_locked:
                continue
            payslips = services.calculate_period(period, self.payroll_user)
            services.change_status(
                period, "VERIFIED", self.payroll_user, "Checked by sampling"
            )
            services.validate(period, self.hr)
            period.refresh_from_db()
            label = f"{first:%m/%Y}: {len(payslips)} payslips validated"
            if offset < -1:
                period.payment_date = add_months(first, 1) - datetime.timedelta(days=3)
                period.save(update_fields=["payment_date"])
                services.change_status(period, "PAID", self.payroll_user)
                for body in ("CNPS", "TAX", "CRTV", "CFC", "FNE", "COMMUNE"):
                    try:
                        accounting.generate_settlement_entry(
                            period,
                            body,
                            self.payroll_user,
                            add_months(first, 1).replace(day=15),
                        )
                    except accounting.AccountingError:
                        pass
                services.change_status(period, "POSTED", self.payroll_user)
                label += ", paid and posted"
            done.append(label)
        # Current month: opened with a few manual inputs.
        first = month_start(self.today)
        period = services.open_period(first.year, first.month, self.payroll_user)
        bonus = SalaryElement.objects.filter(code="PERFORMANCE").first()
        if bonus is not None:
            for employee in self.by_department.get("COM", [])[1:5]:
                VariableInput.objects.get_or_create(
                    period=period,
                    employee=employee,
                    element=bonus,
                    defaults={
                        "amount": Decimal(self.rng.choice([25000, 50000, 75000]))
                    },
                )
        done.append(f"{first:%m/%Y}: opened with sales bonuses")
        return "; ".join(done)

    def seed_budgets(self):
        from accounting.models import Budget
        from payroll.models import Payslip

        year = self.today.year
        count = 0
        for code, department in self.departments.items():
            monthly = sum(
                (p.gross + p.employer_contributions)
                for p in Payslip.objects.filter(
                    employee__department=department,
                    period__year=year,
                    status="VALIDATED",
                )
            )
            months = (
                Payslip.objects.filter(period__year=year, status="VALIDATED")
                .values("period__month")
                .distinct()
                .count()
            ) or 1
            amount = (Decimal(monthly) / months * 12 * Decimal("1.05")).quantize(
                Decimal("1000")
            )
            if amount:
                Budget.objects.get_or_create(
                    year=year, department=department, defaults={"amount": amount}
                )
                count += 1
        return f"{count} department budgets for {year}"

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def seed_planning(self):
        from planning import services
        from planning.models import Shift, Timetable

        shifts = {s.code: s for s in Shift.objects.all()}
        team = [
            e for e in self.by_department.get("LOG", []) if e != self.heads.get("LOG")
        ]
        if not team or not shifts:
            return "skipped (no team or shift)"
        monday = self.today + datetime.timedelta(
            days=(7 - self.today.weekday()) % 7 or 7
        )
        published = Timetable.objects.create(
            name=f"Garoua depot – weeks {monday.isocalendar()[1]}-{monday.isocalendar()[1] + 1}",
            department=self.departments["LOG"],
            start_date=monday,
            end_date=monday + datetime.timedelta(days=13),
            created_by=self.hr,
        )
        rotation = ["M", "A", "N"]
        entries = 0
        for index, employee in enumerate(team):
            for offset in range(14):
                day = monday + datetime.timedelta(days=offset)
                if day.weekday() == 6:
                    continue
                code = rotation[(index + offset // 7) % 3] if day.weekday() < 5 else "D"
                if code in shifts:
                    services.add_entry(
                        published, employee, day, shifts[code], force=True
                    )
                    entries += 1
        services.publish(published, self.hr)
        draft = Timetable.objects.create(
            name="Garoua depot – end of year draft",
            department=self.departments["LOG"],
            start_date=monday + datetime.timedelta(days=14),
            end_date=monday + datetime.timedelta(days=27),
            created_by=self.hr,
        )
        for employee in team[:4]:
            for offset in range(5):
                services.add_entry(
                    draft,
                    employee,
                    draft.start_date + datetime.timedelta(days=offset),
                    shifts.get("D") or next(iter(shifts.values())),
                    force=True,
                )
                entries += 1
        return f"2 timetables (1 published), {entries} shifts"

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def seed_training(self):
        from training import services
        from training.models import (
            Participation,
            TrainingNeed,
            TrainingPlan,
            TrainingSession,
        )

        year = self.today.year
        plan, _ = TrainingPlan.objects.get_or_create(
            year=year,
            defaults={
                "budget": Decimal(18000000),
                "status": "APPROVED",
                "notes": "Priorities: safety, digital skills, management.",
            },
        )
        sessions = [
            (
                "Occupational health and safety (SST)",
                "SafeWork Training Centre",
                "LOG",
                -120,
                2,
                "Garoua depot",
                1200000,
                24,
                "Occupational health and safety",
            ),
            (
                "Advanced Excel for finance",
                "Digital Academy Douala",
                "DAF",
                -50,
                3,
                "Douala head office",
                850000,
                None,
                "Excel (advanced)",
            ),
            (
                "Cameroon payroll: CNPS and IRPP updates",
                "Cabinet Fiscal Conseil",
                "DRH",
                -30,
                2,
                "Douala head office",
                600000,
                None,
                "Cameroon payroll and CNPS",
            ),
            (
                "Leadership for managers",
                "Leadership Institute",
                None,
                -1,
                3,
                "Hôtel Akwa Palace, Douala",
                3500000,
                None,
                "Leadership",
            ),
            (
                "Customer service excellence",
                "Service Pro Academy",
                "SAV",
                25,
                2,
                "Yaoundé agency",
                900000,
                None,
                "Customer relationship",
            ),
            (
                "Cybersecurity awareness",
                "CyberSafe Africa",
                "IT",
                40,
                1,
                "Online",
                400000,
                None,
                "Network administration",
            ),
            (
                "Forklift driving licence",
                "SafeWork Training Centre",
                "LOG",
                55,
                5,
                "Garoua depot",
                1500000,
                36,
                "Forklift driving",
            ),
        ]
        participations = 0
        for (
            title,
            organiser,
            dept,
            start_in,
            days,
            place,
            cost,
            validity,
            skill,
        ) in sessions:
            start = self._next_weekday(self.today + datetime.timedelta(days=start_in))
            session = TrainingSession.objects.create(
                plan=plan,
                title=title,
                organiser=organiser,
                trainer=f"{self.rng.choice(MALE_NAMES + FEMALE_NAMES)} {self.rng.choice(SURNAMES)}",
                description=f"{title}: theory and practical cases.",
                start_date=start,
                end_date=start + datetime.timedelta(days=days - 1),
                place=place,
                cost=Decimal(cost),
                max_participants=15,
                certificate_validity_months=validity,
            )
            if skill in getattr(self, "skills", {}):
                session.skills.add(self.skills[skill])
            if dept:
                people = self.by_department.get(dept, [])[:8]
            else:
                people = list(self.heads.values())[:10]
            services.register(session, people, self.hr)
            participations += len(people)
            if start_in < -2:
                for participation in session.participations.all():
                    attended = self.rng.random() > 0.08
                    services.record_result(
                        participation,
                        {
                            "status": "ATTENDED" if attended else "ABSENT",
                            "result": (
                                ("PASSED" if self.rng.random() > 0.15 else "FAILED")
                                if attended
                                else "PENDING"
                            ),
                            "satisfaction": self.rng.randint(3, 5),
                            "effectiveness": self.rng.randint(2, 5),
                        },
                        self.hr,
                    )
                services.close_session(session)
            elif start_in <= 0:
                session.status = "ONGOING"
                session.save(update_fields=["status"])
        needs = 0
        population = [e for team in self.by_department.values() for e in team]
        for subject, priority, origin, status in [
            ("Project management (PMP preparation)", "HIGH", "EMPLOYEE", "IDENTIFIED"),
            ("Advanced negotiation techniques", "MEDIUM", "MANAGER", "IDENTIFIED"),
            ("SYSCOHADA revised: closing operations", "HIGH", "HR", "PLANNED"),
            ("Professional English", "LOW", "EMPLOYEE", "IDENTIFIED"),
            ("First aid at work", "MEDIUM", "HR", "IDENTIFIED"),
            ("React advanced patterns", "MEDIUM", "EVALUATION", "IDENTIFIED"),
            ("Stock management with barcodes", "LOW", "MANAGER", "REJECTED"),
            ("Labour law: disciplinary procedure", "HIGH", "HR", "DONE"),
        ]:
            employee = self.rng.choice(population)
            TrainingNeed.objects.create(
                employee=employee,
                department=employee.department,
                subject=subject,
                priority=priority,
                year=year,
                origin=origin,
                status=status,
                estimated_cost=Decimal(
                    self.rng.choice([150000, 300000, 450000, 800000])
                ),
                created_by=employee.user or self.hr,
            )
            needs += 1
        return (
            f"plan {year}, {len(sessions)} sessions, {participations} participations, {needs} needs "
            f"({Participation.objects.filter(result='PASSED').count()} certificates)"
        )

    # ------------------------------------------------------------------
    # Recruitment
    # ------------------------------------------------------------------

    def seed_recruitment(self):
        from recruitment import services
        from recruitment.models import Application, JobOffer, RecruitmentNeed

        head_user = (self.heads.get("ENG01") and self.heads["ENG01"].user) or self.hr
        needs = [
            (
                "ENG01",
                "DEV01",
                2,
                "PERMANENT",
                "Growth of the product team for the new mobile application.",
                "APPROVED",
            ),
            (
                "COM",
                "COM02",
                3,
                "FIXED_TERM",
                "Launch of the Bafoussam market.",
                "APPROVED",
            ),
            (
                "DAF",
                "FIN03",
                1,
                "PERMANENT",
                "Replacement after a resignation.",
                "APPROVED",
            ),
            ("LOG", "LOG04", 2, "FIXED_TERM", "Peak season deliveries.", "SUBMITTED"),
            ("IT", "IT02", 1, "PERMANENT", "Support of the new branch.", "DRAFT"),
        ]
        offers = []
        for dept, p_code, posts, kind, why, status in needs:
            need = RecruitmentNeed.objects.create(
                position=self.positions[p_code],
                department=self.departments[dept],
                number_of_posts=posts,
                contract_type=kind,
                justification=why,
                desired_start=month_start(self.today, 2),
                requested_by=head_user,
            )
            if status == "SUBMITTED":
                services.submit_need(need, head_user)
            elif status == "APPROVED":
                need.status = "APPROVED"
                need.save(update_fields=["status"])
                offer = JobOffer.objects.create(
                    need=need,
                    title=self.positions[p_code].title,
                    position=self.positions[p_code],
                    department=self.departments[dept],
                    location=self.departments[dept].site,
                    contract_type=kind,
                    description=(
                        f"Saint Jean Services is hiring a {self.positions[p_code].title.lower()} "
                        f"for its {self.departments[dept].name} department. {why}"
                    ),
                    requirements="Relevant diploma, 2 years of experience, French and English.",
                    closing_date=self.today
                    + datetime.timedelta(days=self.rng.randint(10, 40)),
                )
                services.publish_offer(offer)
                offers.append(offer)
        closed = JobOffer.objects.create(
            title="Marketing intern",
            position=self.positions["COM03"],
            department=self.departments["COM"],
            location=self.sites["YDE01"],
            contract_type="INTERNSHIP",
            description="Six-month internship in marketing.",
            closing_date=self.today - datetime.timedelta(days=20),
            status="CLOSED",
            published_at=timezone.now() - datetime.timedelta(days=60),
        )
        offers.append(closed)
        paths = [
            [],
            ["PRESELECTED"],
            ["PRESELECTED", "INTERVIEW"],
            ["PRESELECTED", "TEST"],
            ["PRESELECTED", "INTERVIEW", "SELECTED"],
            ["REJECTED"],
            ["PRESELECTED", "INTERVIEW", "REJECTED"],
        ]
        applications = 0
        for offer in offers:
            for _ in range(self.rng.randint(3, 6)):
                sex = self.rng.choice("MF")
                surname, given = self._name(sex)
                city, _ = self.rng.choice(CITIES)
                application = Application.objects.create(
                    offer=offer,
                    surname=surname,
                    given_names=given,
                    email=f"{ascii_slug(given)}.{ascii_slug(surname)}@yahoo.fr",
                    phone=f"+237 6{self.rng.choice('5789')}{self.rng.randint(1000000, 9999999)}",
                    date_of_birth=datetime.date(
                        self.today.year - self.rng.randint(22, 40),
                        self.rng.randint(1, 12),
                        10,
                    ),
                    place_of_birth=city,
                    sex=sex,
                    nationality="Cameroonian",
                    marital_status="SINGLE",
                    address=city,
                    motivation="I am very interested in joining Saint Jean Services.",
                    score=self.rng.randint(35, 92),
                    source=self.rng.choice(
                        ["PUBLIC", "PUBLIC", "REFERRAL", "LINKEDIN"]
                    ),
                )
                services.receive(application)
                for stage in self.rng.choice(paths):
                    services.move(application, stage, self.hr, "Demonstration")
                applications += 1
        return (
            f"{len(needs)} needs, {len(offers)} job offers, {applications} applications"
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def seed_evaluation(self):
        from evaluation import services
        from evaluation.models import Campaign, Objective

        criteria = [
            {"code": "QUALITY", "label": "Quality of work", "weight": 3},
            {"code": "PRODUCTIVITY", "label": "Productivity", "weight": 2},
            {"code": "TEAMWORK", "label": "Team work", "weight": 2},
            {"code": "INITIATIVE", "label": "Initiative", "weight": 1},
            {"code": "DISCIPLINE", "label": "Punctuality and discipline", "weight": 1},
        ]
        results = []
        for year, status in (
            (self.today.year - 1, "CLOSED"),
            (self.today.year, "OPEN"),
        ):
            campaign = Campaign.objects.create(
                name=f"Annual evaluation {year}",
                year=year,
                start_date=datetime.date(year, 10 if status == "OPEN" else 11, 1),
                end_date=datetime.date(year, 11 if status == "OPEN" else 12, 15),
                criteria=criteria,
                scale_max=5,
                objectives_weight=50,
                created_by=self.hr,
            )
            services.open_campaign(campaign, self.hr)
            evaluations = list(campaign.evaluations.select_related("evaluator"))
            share_self = 1.0 if status == "CLOSED" else 0.55
            share_manager = 1.0 if status == "CLOSED" else 0.3
            for index, evaluation in enumerate(evaluations):
                ratio = index / max(len(evaluations), 1)
                if ratio >= share_self:
                    continue
                services.submit_self(
                    evaluation,
                    {c["code"]: self.rng.randint(3, 5) for c in criteria},
                    "I reached most of my objectives this year.",
                )
                if ratio >= share_manager:
                    continue
                for title in self.rng.sample(
                    [
                        "Reach the sales / activity target",
                        "Reduce the processing delays",
                        "Train a new colleague",
                        "Complete the certification",
                        "Improve the customer satisfaction",
                    ],
                    2,
                ):
                    Objective.objects.create(
                        evaluation=evaluation,
                        title=title,
                        weight=self.rng.randint(1, 3),
                        target="100 %",
                        achievement_percent=Decimal(self.rng.randint(60, 115)),
                    )
                proposal = self.rng.choice(
                    ["NONE", "NONE", "NONE", "TRAINING", "BONUS"]
                )
                evaluation.refresh_from_db()
                data = {
                    "manager_scores": {
                        c["code"]: self.rng.randint(2, 5) for c in criteria
                    },
                    "manager_comment": "Good year overall.",
                    "strengths": self.rng.choice(
                        [
                            "Reliable and rigorous.",
                            "Very good team spirit.",
                            "Strong technical skills.",
                        ]
                    ),
                    "improvements": self.rng.choice(
                        ["Delegation.", "Written reporting.", "Punctuality."]
                    ),
                    "proposal": proposal,
                    "training_subject": (
                        "Project management" if proposal == "TRAINING" else ""
                    ),
                }
                if proposal == "BONUS":
                    data["bonus_amount"] = Decimal(100000)
                services.submit_manager(
                    evaluation, evaluation.evaluator or self.hr, data
                )
                if status == "CLOSED":
                    evaluation.refresh_from_db()
                    evaluation.proposal_applied = (
                        True  # last year's proposals are history
                    )
                    evaluation.status = "VALIDATED"
                    evaluation.validated_at = timezone.now()
                    evaluation.save()
            if status == "CLOSED":
                campaign.status = "CLOSED"
                campaign.save(update_fields=["status"])
            results.append(f"{campaign.name}: {len(evaluations)} evaluations")
        return "; ".join(results)

    # ------------------------------------------------------------------
    # Documents and self-service requests
    # ------------------------------------------------------------------

    def seed_documents(self):
        from documents.services import issue_document
        from documents.views import certificate_context
        from employees.models import CorrectionRequest
        from notifications.services import start_approval

        population = [e for team in self.by_department.values() for e in team]
        issued = 0
        for employee in self.rng.sample(population, min(6, len(population))):
            for code in ("WORK_CERTIFICATE", "PRESENCE_ATTESTATION"):
                try:
                    issue_document(
                        code,
                        certificate_context(code, employee, self.hr),
                        employee=employee,
                        user=self.hr,
                    )
                    issued += 1
                except Exception:
                    pass
        corrections = 0
        for employee in [e for e in population if e.user_id][:3]:
            item = CorrectionRequest.objects.create(
                employee=employee,
                field_name="phone_number",
                current_value=employee.phone_number,
                requested_value=f"+237 67{self.rng.randint(1000000, 9999999)}",
                reason="New phone number",
            )
            start_approval(item, "PROFILE_CORRECTION", employee.user)
            corrections += 1
        return f"{issued} documents issued, {corrections} record corrections pending"
