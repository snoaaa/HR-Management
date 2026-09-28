"""
Tests for M-17 - Security, Roles and Audit (BN-169 .. BN-177).

Each TestCase below is named after the business need it exercises so the
mapping between the Expression of Need and the automated coverage stays
obvious.
"""

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    Action,
    AuditLog,
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
from .services import (
    generate_two_factor_secret,
    set_user_password,
    verify_two_factor_code,
)


def make_role(name, module, actions, scope=Scope.OWN, requires_two_factor=False):
    role = Role.objects.create(
        name=name, scope=scope, requires_two_factor=requires_two_factor
    )
    for action in actions:
        RolePermission.objects.create(role=role, module=module, action=action)
    return role


def grant(user, role, assigned_by=None):
    UserRole.objects.create(user=user, role=role, assigned_by=assigned_by)


class BN169IndividualAuthenticationTests(TestCase):
    """BN-169 - every user authenticates individually; no shared accounts."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alice", password="Correct-Horse9!", must_change_password=False
        )

    def test_login_requires_correct_credentials_for_that_specific_account(self):
        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_succeeds_with_own_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "Correct-Horse9!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["username"], "alice")

    def test_repeated_failures_lock_the_individual_account(self):
        for _ in range(5):
            self.client.post(
                reverse("login"),
                {"username": "alice", "password": "wrong"},
                format="json",
            )
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.locked_until)
        self.assertGreater(self.user.locked_until, timezone.now())

        response = self.client.post(
            reverse("login"),
            {"username": "alice", "password": "Correct-Horse9!"},
            format="json",
        )
        self.assertEqual(response.status_code, 423)


class BN170FineGrainedPermissionTests(TestCase):
    """BN-170 - permissions are granted per module and per action."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="bob", password="Sup3r-Secret!", must_change_password=False
        )
        self.client.force_authenticate(self.user)

    def test_no_role_means_no_access_to_a_module(self):
        response = self.client.get("/api/roles/")
        self.assertEqual(response.status_code, 403)

    def test_consult_only_role_cannot_create(self):
        role = make_role(
            "Reader", Module.ADMIN, [Action.CONSULT], scope=Scope.ORGANISATION
        )
        grant(self.user, role)
        self.assertEqual(self.client.get("/api/roles/").status_code, 200)
        self.assertEqual(
            self.client.post("/api/roles/", {"name": "New role"}).status_code, 403
        )

    def test_denied_access_is_itself_audited(self):
        self.client.get("/api/roles/")
        self.assertTrue(
            AuditLog.objects.filter(
                action="access_denied", module=Module.ADMIN
            ).exists()
        )


class BN171VisibilityPerimeterTests(TestCase):
    """BN-171 - data visibility restricted per own/team/department/site/org."""

    def setUp(self):
        self.site = Site.objects.create(name="Paris HQ", code="PAR")
        self.dept_a = Department.objects.create(
            name="Engineering", code="ENG", site=self.site
        )
        self.dept_b = Department.objects.create(
            name="Sales", code="SLS", site=self.site
        )
        self.team_a1 = Team.objects.create(name="Backend", department=self.dept_a)

        self.manager = User.objects.create_user(
            username="dept-manager",
            password="Manager-Pass9!",
            must_change_password=False,
            department=self.dept_a,
        )
        self.employee_same_dept = User.objects.create_user(
            username="dev1",
            password="pw",
            must_change_password=False,
            department=self.dept_a,
            team=self.team_a1,
        )
        self.employee_other_dept = User.objects.create_user(
            username="sales1",
            password="pw",
            must_change_password=False,
            department=self.dept_b,
        )

        role = make_role(
            "Department Payroll Viewer",
            Module.PAYROLL,
            [Action.CONSULT],
            scope=Scope.DEPARTMENT,
        )
        grant(self.manager, role)
        self.manager.is_payroll_authorized = True
        self.manager.save(update_fields=["is_payroll_authorized"])

        SalaryRecord.objects.create(
            employee=self.employee_same_dept,
            base_salary="3000.00",
            effective_date="2026-01-01",
        )
        SalaryRecord.objects.create(
            employee=self.employee_other_dept,
            base_salary="3200.00",
            effective_date="2026-01-01",
        )

        self.client = APIClient()
        self.client.force_authenticate(self.manager)
        # This account is payroll-authorised, so BN-176 also requires a
        # verified second factor; bypass it here since 2FA itself is
        # covered separately by BN176TwoFactorTests.
        session = self.client.session
        session["two_factor_verified"] = True
        session.save()

    def test_department_scope_hides_other_departments_data(self):
        response = self.client.get("/api/salary-records/")
        self.assertEqual(response.status_code, 200)
        employees = {row["employee"] for row in response.data["results"]}
        self.assertIn(self.employee_same_dept.pk, employees)
        self.assertNotIn(self.employee_other_dept.pk, employees)


class BN172SalaryConfidentialityTests(TestCase):
    """BN-172 - salary data only for accounts explicitly authorised for payroll."""

    def setUp(self):
        self.employee = User.objects.create_user(
            username="carol", password="pw", must_change_password=False
        )
        SalaryRecord.objects.create(
            employee=self.employee, base_salary="4000.00", effective_date="2026-01-01"
        )

        self.viewer = User.objects.create_user(
            username="hr1", password="pw", must_change_password=False
        )
        role = make_role(
            "Payroll Reader", Module.PAYROLL, [Action.CONSULT], scope=Scope.ORGANISATION
        )
        grant(self.viewer, role)

        self.client = APIClient()
        self.client.force_authenticate(self.viewer)

    def test_module_permission_alone_is_not_enough(self):
        # Has the PAYROLL/CONSULT grant, but is NOT flagged is_payroll_authorized.
        response = self.client.get("/api/salary-records/")
        self.assertEqual(response.status_code, 403)

    def test_payroll_authorization_flag_unlocks_access(self):
        self.viewer.is_payroll_authorized = True
        self.viewer.save(update_fields=["is_payroll_authorized"])
        # Being payroll-authorised also triggers the BN-176 second-factor
        # requirement; bypass it here to isolate the BN-172 flag itself.
        session = self.client.session
        session["two_factor_verified"] = True
        session.save()

        response = self.client.get("/api/salary-records/")
        self.assertEqual(response.status_code, 200)


class BN173And175AuditTrailTests(TestCase):
    """BN-173 - immutable audit trail; BN-175 - consultable/exportable, never editable."""

    def test_audit_entries_cannot_be_updated(self):
        entry = AuditLog.objects.create(
            action="create", module=Module.EMPLOYEES, object_repr="x"
        )
        entry.notes = "trying to rewrite history"
        with self.assertRaises(PermissionDenied):
            entry.save()

    def test_audit_entries_cannot_be_deleted(self):
        entry = AuditLog.objects.create(
            action="create", module=Module.EMPLOYEES, object_repr="x"
        )
        with self.assertRaises(PermissionDenied):
            entry.delete()

    def test_salary_record_changes_are_recorded_with_before_and_after(self):
        employee = User.objects.create_user(
            username="dave", password="pw", must_change_password=False
        )
        record = SalaryRecord.objects.create(
            employee=employee, base_salary="1000.00", effective_date="2026-01-01"
        )
        record.base_salary = "1200.00"
        record.save()

        entries = AuditLog.objects.filter(
            object_type="SalaryRecord", object_id=str(record.pk)
        ).order_by("id")
        self.assertEqual(entries.count(), 2)
        creation, update = entries
        self.assertEqual(creation.action, "create")
        self.assertIsNone(creation.previous_value)
        self.assertEqual(update.action, "update")
        self.assertEqual(update.previous_value["base_salary"], "1000.00")
        self.assertEqual(update.new_value["base_salary"], "1200.00")

    def test_authorised_user_can_consult_and_export_the_trail(self):
        AuditLog.objects.create(
            action="create", module=Module.EMPLOYEES, object_repr="x"
        )
        user = User.objects.create_user(
            username="auditor", password="pw", must_change_password=False
        )
        role = make_role(
            "Auditor",
            Module.AUDIT,
            [Action.CONSULT, Action.EXPORT],
            scope=Scope.ORGANISATION,
        )
        grant(user, role)

        client = APIClient()
        client.force_authenticate(user)

        listing = client.get("/api/audit-log/")
        self.assertEqual(listing.status_code, 200)

        export = client.get("/api/audit-log/export/")
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "text/csv")

    def test_audit_trail_has_no_write_routes_at_all(self):
        user = User.objects.create_user(
            username="auditor2", password="pw", must_change_password=False
        )
        role = make_role(
            "Auditor2", Module.AUDIT, [Action.CONSULT], scope=Scope.ORGANISATION
        )
        grant(user, role)
        client = APIClient()
        client.force_authenticate(user)
        response = client.post(
            "/api/audit-log/", {"action": "create", "module": "admin"}
        )
        # ReadOnlyModelViewSet never wires up a "create" handler, so POST
        # maps to no action at all; HasModulePermission then denies it
        # outright (fail-closed) before DRF even gets to a routing-level
        # 405. Either way, BN-175 holds: there is no way to write here.
        self.assertEqual(response.status_code, 403)


class BN174PasswordPolicyTests(TestCase):
    """
    BN-174 - password policy, forced change at first login, idle timeout.

    These go through the *real* login endpoint (rather than
    `force_authenticate`) because ForcePasswordChangeMiddleware and
    SessionTimeoutMiddleware read Django's own session-backed
    `request.user`, which only reflects an authenticated user once a real
    session has been established via `LoginView`.
    """

    def test_weak_password_is_rejected(self):
        user = User(username="weakpw")
        with self.assertRaises(Exception):
            set_user_password(user, "abc")

    def test_new_account_must_change_password_before_using_other_endpoints(self):
        User.objects.create_user(username="newhire", password="Temp-Passw0rd!")
        client = APIClient()

        login = client.post(
            reverse("login"),
            {"username": "newhire", "password": "Temp-Passw0rd!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["must_change_password"])

        blocked = client.get("/api/roles/")
        self.assertEqual(blocked.status_code, 403)
        # This 403 comes from our own ForcePasswordChangeMiddleware, which
        # returns a plain Django JsonResponse (no DRF `.data`), unlike the
        # DRF-permission-denied 403s elsewhere in this test.
        self.assertEqual(blocked.json().get("code"), "password_change_required")

        changed = client.post(
            reverse("password-change"),
            {"current_password": "Temp-Passw0rd!", "new_password": "Br4nd-New-Pass!"},
            format="json",
        )
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(User.objects.get(username="newhire").must_change_password)

        # No longer blocked by the forced-change middleware; still 403, but
        # now for the ordinary reason of holding no role at all.
        after = client.get("/api/roles/")
        self.assertEqual(after.status_code, 403)
        self.assertIsNone(after.data.get("code"))

    def test_cannot_reuse_a_recent_password(self):
        user = User.objects.create_user(username="reuser", password="First-Passw0rd!")
        set_user_password(user, "Second-Passw0rd!")
        with self.assertRaises(Exception):
            set_user_password(user, "First-Passw0rd!")

    def test_idle_session_is_closed(self):
        User.objects.create_user(
            username="idler", password="Idle-Passw0rd!", must_change_password=False
        )
        client = APIClient()
        login = client.post(
            reverse("login"),
            {"username": "idler", "password": "Idle-Passw0rd!"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)

        user = User.objects.get(username="idler")
        user.last_activity = timezone.now() - timezone.timedelta(minutes=45)
        user.save(update_fields=["last_activity"])

        response = client.get(reverse("current-user"))
        self.assertEqual(response.status_code, 401)


class BN176TwoFactorTests(TestCase):
    """BN-176 - second authentication factor for payroll-authorised profiles."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="payroll-officer",
            password="pw",
            must_change_password=False,
            is_payroll_authorized=True,
        )
        role = make_role(
            "Payroll Full", Module.PAYROLL, [Action.CONSULT], scope=Scope.ORGANISATION
        )
        grant(self.user, role)
        SalaryRecord.objects.create(
            employee=self.user, base_salary="1.00", effective_date="2026-01-01"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_payroll_access_blocked_until_second_factor_verified(self):
        self.assertTrue(self.user.requires_two_factor())
        response = self.client.get("/api/salary-records/")
        self.assertEqual(response.status_code, 403)

    def test_verifying_a_valid_code_unlocks_access_for_the_session(self):
        secret = generate_two_factor_secret()
        self.user.two_factor_secret = secret
        self.user.save(update_fields=["two_factor_secret"])

        import pyotp

        code = pyotp.TOTP(secret).now()
        self.assertTrue(verify_two_factor_code(secret, code))

        verify = self.client.post(
            reverse("two-factor-verify"), {"code": code}, format="json"
        )
        self.assertEqual(verify.status_code, 200)

        response = self.client.get("/api/salary-records/")
        self.assertEqual(response.status_code, 200)


class BN177GDPRTests(TestCase):
    """BN-177 - purpose/minimisation/retention/right of access & rectification."""

    def setUp(self):
        self.role = make_role(
            "Employee (Self-Service)",
            Module.EMPLOYEES,
            [Action.CONSULT, Action.CREATE],
            scope=Scope.OWN,
        )
        self.employee = User.objects.create_user(
            username="emma", password="pw", must_change_password=False
        )
        grant(self.employee, self.role)
        self.client = APIClient()
        self.client.force_authenticate(self.employee)

    def test_processing_purpose_is_disclosed_on_the_account(self):
        self.assertTrue(self.employee.processing_purpose)

    def test_employee_can_raise_and_consult_their_own_request(self):
        response = self.client.post(
            "/api/data-subject-requests/",
            {"request_type": "access", "details": "Please send me a copy of my file."},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["employee"], self.employee.pk)

        listing = self.client.get("/api/data-subject-requests/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data["results"]), 1)

    def test_employee_cannot_see_another_employees_request(self):
        other = User.objects.create_user(
            username="frank", password="pw", must_change_password=False
        )
        grant(other, self.role)
        other_client = APIClient()
        other_client.force_authenticate(other)
        other_client.post(
            "/api/data-subject-requests/",
            {"request_type": "rectification", "details": "Fix my name."},
        )

        listing = self.client.get("/api/data-subject-requests/")
        self.assertEqual(listing.data["results"], [])
