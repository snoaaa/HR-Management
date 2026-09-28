"""
Command to seed comprehensive security data, roles, organizational perimeters,
demo accounts, salary records, and GDPR requests for Module 17.

    python manage.py seed_security
"""

from datetime import date
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import (
    Action,
    AuditAction,
    AuditLog,
    DataSubjectRequest,
    Department,
    Module,
    Role,
    RolePermission,
    SalaryRecord,
    Scope,
    Site,
    Team,
    User,
    UserRole,
)
from api.services import set_user_password

DEFAULT_ROLES = [
    {
        "name": "HR Administrator",
        "description": "Full access to every module, organisation-wide.",
        "scope": Scope.ORGANISATION,
        "requires_two_factor": True,
        "grants": [
            (module, action) for module in Module.values for action in Action.values
        ],
    },
    {
        "name": "Payroll Officer",
        "description": "Manages compensation for the whole organisation.",
        "scope": Scope.ORGANISATION,
        "requires_two_factor": True,
        "grants": [
            (Module.PAYROLL, Action.CONSULT),
            (Module.PAYROLL, Action.CREATE),
            (Module.PAYROLL, Action.MODIFY),
            (Module.PAYROLL, Action.PRINT),
            (Module.PAYROLL, Action.EXPORT),
            (Module.EMPLOYEES, Action.CONSULT),
        ],
    },
    {
        "name": "Department Manager",
        "description": "Consults and validates HR data for their department.",
        "scope": Scope.DEPARTMENT,
        "requires_two_factor": False,
        "grants": [
            (Module.EMPLOYEES, Action.CONSULT),
            (Module.LEAVE, Action.CONSULT),
            (Module.LEAVE, Action.VALIDATE),
            (Module.PERFORMANCE, Action.CONSULT),
            (Module.PERFORMANCE, Action.MODIFY),
        ],
    },
    {
        "name": "Employee (Self-Service)",
        "description": "Every employee's baseline: their own data only.",
        "scope": Scope.OWN,
        "requires_two_factor": False,
        "grants": [
            (Module.EMPLOYEES, Action.CONSULT),
            (Module.EMPLOYEES, Action.CREATE),
            (Module.LEAVE, Action.CONSULT),
            (Module.LEAVE, Action.CREATE),
            (Module.DOCUMENTS, Action.CONSULT),
        ],
    },
    {
        "name": "Security & Audit Officer",
        "description": "BN-175 - consults and exports the audit trail; manages roles.",
        "scope": Scope.ORGANISATION,
        "requires_two_factor": True,
        "grants": [
            (Module.AUDIT, Action.CONSULT),
            (Module.AUDIT, Action.EXPORT),
            (Module.ADMIN, Action.CONSULT),
            (Module.ADMIN, Action.CREATE),
            (Module.ADMIN, Action.MODIFY),
        ],
    },
]


class Command(BaseCommand):
    help = "Seeds organizational perimeters, roles, users, and M-17 security demo data."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding Sites, Departments, and Teams...")
        site_hq, _ = Site.objects.get_or_create(name="Douala Headquarters", code="DLA-HQ")
        site_yde, _ = Site.objects.get_or_create(name="Yaounde Regional Office", code="YDE-RO")

        dept_hr, _ = Department.objects.get_or_create(name="Human Resources", code="HR", site=site_hq)
        dept_fin, _ = Department.objects.get_or_create(name="Finance & Accounting", code="FIN", site=site_hq)
        dept_swe, _ = Department.objects.get_or_create(name="Software Engineering", code="SWE", site=site_hq)
        dept_ops, _ = Department.objects.get_or_create(name="Operations & Logistics", code="OPS", site=site_yde)

        team_chr, _ = Team.objects.get_or_create(name="Core HR & Talent", department=dept_hr)
        team_pay, _ = Team.objects.get_or_create(name="Compensation & Benefits", department=dept_fin)
        team_fe, _ = Team.objects.get_or_create(name="Frontend Engineering", department=dept_swe)
        team_be, _ = Team.objects.get_or_create(name="Backend Engineering", department=dept_swe)
        team_infra, _ = Team.objects.get_or_create(name="Infrastructure & DevOps", department=dept_ops)

        self.stdout.write("Seeding Roles and Permissions...")
        roles_dict = {}
        for spec in DEFAULT_ROLES:
            role, created = Role.objects.update_or_create(
                name=spec["name"],
                defaults={
                    "description": spec["description"],
                    "scope": spec["scope"],
                    "requires_two_factor": spec["requires_two_factor"],
                    "is_active": True,
                },
            )
            roles_dict[spec["name"]] = role
            for module, action in spec["grants"]:
                RolePermission.objects.get_or_create(
                    role=role, module=module, action=action
                )

        self.stdout.write("Seeding Demo Users...")
        # Common TOTP secret for demo convenience (generates valid codes or can use authenticator app)
        demo_totp_secret = "JBSWY3DPEHPK3PXP"

        # 1. Admin / Security Officer
        admin, _ = User.objects.update_or_create(
            username="admin",
            defaults={
                "first_name": "System",
                "last_name": "Administrator",
                "email": "admin@hrms-enterprise.com",
                "employee_id": "EMP-001",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "site": site_hq,
                "department": dept_hr,
                "team": team_chr,
                "is_payroll_authorized": True,
                "two_factor_enabled": True,
                "two_factor_secret": demo_totp_secret,
                "must_change_password": False,
                "data_processing_consent": True,
                "consent_given_at": timezone.now(),
            },
        )
        set_user_password(admin, "Antigravity#2026!", forced=True)
        UserRole.objects.get_or_create(user=admin, role=roles_dict["Security & Audit Officer"])
        UserRole.objects.get_or_create(user=admin, role=roles_dict["HR Administrator"])

        # 2. HR Manager
        hr_mgr, _ = User.objects.update_or_create(
            username="hr_manager",
            defaults={
                "first_name": "HR",
                "last_name": "Manager",
                "email": "hr.manager@hrms-enterprise.com",
                "employee_id": "EMP-002",
                "is_staff": False,
                "is_active": True,
                "site": site_hq,
                "department": dept_hr,
                "team": team_chr,
                "is_payroll_authorized": True,
                "two_factor_enabled": True,
                "two_factor_secret": demo_totp_secret,
                "must_change_password": False,
                "data_processing_consent": True,
                "consent_given_at": timezone.now(),
            },
        )
        set_user_password(hr_mgr, "Corporate#HR2026!", forced=True)
        UserRole.objects.get_or_create(user=hr_mgr, role=roles_dict["HR Administrator"])

        # 3. Payroll Officer
        payroll_off, _ = User.objects.update_or_create(
            username="payroll_officer",
            defaults={
                "first_name": "Payroll",
                "last_name": "Officer",
                "email": "payroll.officer@hrms-enterprise.com",
                "employee_id": "EMP-003",
                "is_staff": False,
                "is_active": True,
                "site": site_hq,
                "department": dept_fin,
                "team": team_pay,
                "is_payroll_authorized": True,
                "two_factor_enabled": True,
                "two_factor_secret": demo_totp_secret,
                "must_change_password": False,
                "data_processing_consent": True,
                "consent_given_at": timezone.now(),
            },
        )
        set_user_password(payroll_off, "Payroll#Sec2026!", forced=True)
        UserRole.objects.get_or_create(user=payroll_off, role=roles_dict["Payroll Officer"])

        # 4. Department Manager (Engineering)
        dept_mgr, _ = User.objects.update_or_create(
            username="dept_manager",
            defaults={
                "first_name": "Department",
                "last_name": "Manager",
                "email": "dept.manager@hrms-enterprise.com",
                "employee_id": "EMP-004",
                "is_staff": False,
                "is_active": True,
                "site": site_hq,
                "department": dept_swe,
                "team": team_be,
                "is_payroll_authorized": False,  # Note: Department manager cannot see salaries
                "two_factor_enabled": False,
                "must_change_password": False,
                "data_processing_consent": True,
                "consent_given_at": timezone.now(),
            },
        )
        set_user_password(dept_mgr, "Engineering#2026!", forced=True)
        UserRole.objects.get_or_create(user=dept_mgr, role=roles_dict["Department Manager"])

        # 5. Employee Alice (Frontend Developer)
        alice, _ = User.objects.update_or_create(
            username="employee_alice",
            defaults={
                "first_name": "Frontend",
                "last_name": "Developer",
                "email": "frontend.dev@hrms-enterprise.com",
                "employee_id": "EMP-005",
                "is_staff": False,
                "is_active": True,
                "site": site_hq,
                "department": dept_swe,
                "team": team_fe,
                "manager": dept_mgr,
                "is_payroll_authorized": False,
                "two_factor_enabled": False,
                "must_change_password": False,
                "data_processing_consent": True,
                "consent_given_at": timezone.now(),
            },
        )
        set_user_password(alice, "AliceDev#2026!", forced=True)
        UserRole.objects.get_or_create(user=alice, role=roles_dict["Employee (Self-Service)"])

        # 6. Employee Bob (DevOps Engineer)
        bob, _ = User.objects.update_or_create(
            username="employee_bob",
            defaults={
                "first_name": "DevOps",
                "last_name": "Engineer",
                "email": "devops.eng@hrms-enterprise.com",
                "employee_id": "EMP-006",
                "is_staff": False,
                "is_active": True,
                "site": site_yde,
                "department": dept_ops,
                "team": team_infra,
                "is_payroll_authorized": False,
                "two_factor_enabled": False,
                "must_change_password": False,
                "data_processing_consent": True,
                "consent_given_at": timezone.now(),
            },
        )
        set_user_password(bob, "BobDev#2026!", forced=True)
        UserRole.objects.get_or_create(user=bob, role=roles_dict["Employee (Self-Service)"])

        # 7. New Hire (Demonstrates First Connection Forced Password Change)
        new_hire, _ = User.objects.update_or_create(
            username="new_hire",
            defaults={
                "first_name": "New",
                "last_name": "Hire",
                "email": "new.hire@hrms-enterprise.com",
                "employee_id": "EMP-007",
                "is_staff": False,
                "is_active": True,
                "site": site_hq,
                "department": dept_swe,
                "team": team_be,
                "manager": dept_mgr,
                "is_payroll_authorized": False,
                "two_factor_enabled": False,
                "must_change_password": True,  # Forced password change required!
                "data_processing_consent": False,
            },
        )
        set_user_password(new_hire, "Welcome#Staff2026!", forced=True)

        UserRole.objects.get_or_create(user=new_hire, role=roles_dict["Employee (Self-Service)"])

        self.stdout.write("Seeding Confidential Salary Records...")
        SalaryRecord.objects.get_or_create(
            employee=admin,
            defaults={"base_salary": "2500000.00", "currency": "XAF", "effective_date": date(2026, 1, 1), "notes": "Executive Director remuneration"}
        )
        SalaryRecord.objects.get_or_create(
            employee=hr_mgr,
            defaults={"base_salary": "1800000.00", "currency": "XAF", "effective_date": date(2026, 1, 1), "notes": "HR Director base compensation"}
        )
        SalaryRecord.objects.get_or_create(
            employee=payroll_off,
            defaults={"base_salary": "1200000.00", "currency": "XAF", "effective_date": date(2026, 1, 1), "notes": "Senior Payroll Specialist"}
        )
        SalaryRecord.objects.get_or_create(
            employee=dept_mgr,
            defaults={"base_salary": "1450000.00", "currency": "XAF", "effective_date": date(2026, 1, 1), "notes": "Head of Software Engineering"}
        )
        SalaryRecord.objects.get_or_create(
            employee=alice,
            defaults={"base_salary": "850000.00", "currency": "XAF", "effective_date": date(2026, 2, 1), "notes": "Senior Frontend Engineer"}
        )
        SalaryRecord.objects.get_or_create(
            employee=bob,
            defaults={"base_salary": "920000.00", "currency": "XAF", "effective_date": date(2026, 2, 1), "notes": "DevOps & Cloud Specialist"}
        )

        self.stdout.write("Seeding GDPR Data Subject Requests (BN-177)...")
        DataSubjectRequest.objects.get_or_create(
            employee=alice,
            request_type=DataSubjectRequest.RequestType.ACCESS,
            defaults={
                "details": "Requesting a full copy of personal and payroll data recorded under GDPR Article 15.",
                "status": DataSubjectRequest.Status.PENDING,
            }
        )
        DataSubjectRequest.objects.get_or_create(
            employee=bob,
            request_type=DataSubjectRequest.RequestType.RECTIFICATION,
            defaults={
                "details": "Correction of residential address and emergency contact phone number.",
                "status": DataSubjectRequest.Status.COMPLETED,
                "handled_by": hr_mgr,
                "handled_at": timezone.now(),
                "resolution_notes": "Address updated in employee file and confirmed with staff member.",
            }
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded all M-17 Security, Roles, and Audit demo data!"))
