from django.test import TestCase

from core.testing import client_for, make_user
from users.models import AuditLog, RolePermission, User


class SecurityTests(TestCase):
    def setUp(self):
        self.admin = make_user("admin", User.Roles.SYSTEM_ADMINISTRATOR)
        self.employee = make_user("emp", User.Roles.EMPLOYEE)

    def test_audit_log_is_unalterable(self):
        log = AuditLog.objects.create(action="x", module="Test")
        log.action = "changed"
        with self.assertRaises(PermissionError):
            log.save()
        with self.assertRaises(PermissionError):
            log.delete()

    def test_permission_matrix_is_editable(self):
        client = client_for(self.admin)
        matrix = client.get("/api/users/permission-matrix/").json()["matrix"]
        self.assertIn("employees", matrix["HR_MANAGER"])
        matrix["EMPLOYEE"]["organisation"] = []
        response = client.put(
            "/api/users/permission-matrix/", {"matrix": matrix}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            RolePermission.objects.filter(
                role="EMPLOYEE", module="organisation"
            ).exists()
        )
        self.assertEqual(
            client_for(self.employee).get("/api/organisation/sites/").status_code, 403
        )

    def test_employee_cannot_edit_organisation(self):
        response = client_for(self.employee).post(
            "/api/organisation/sites/", {"name": "X", "code": "X"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_my_permissions(self):
        data = client_for(self.employee).get("/api/users/me/permissions/").json()
        self.assertEqual(data["role"], "EMPLOYEE")
        self.assertFalse(data["can_view_salary"])
        self.assertIn("consult", data["permissions"]["leave"])

    def test_audit_export(self):
        AuditLog.objects.create(action="Logged in", module="Authentication")
        response = client_for(self.admin).get("/api/audit-logs/export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Logged in", response.content.decode("utf-8"))
        self.assertEqual(
            client_for(self.employee).get("/api/audit-logs/export/").status_code, 403
        )

    def test_password_policy(self):
        client = client_for(self.employee)
        weak = client.post(
            "/api/auth/change-password/",
            {"old_password": "Passw0rd!", "new_password": "simplepassword"},
            format="json",
        )
        self.assertEqual(weak.status_code, 400)
        strong = client.post(
            "/api/auth/change-password/",
            {"old_password": "Passw0rd!", "new_password": "N3w-Secret!"},
            format="json",
        )
        self.assertEqual(strong.status_code, 200)


class TwoFactorTests(TestCase):
    """BN-176."""

    def test_rfc_6238_vector(self):
        from users import totp

        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # "12345678901234567890"
        self.assertEqual(totp.code_at(secret, 59), "287082")
        self.assertEqual(totp.code_at(secret, 1111111109), "081804")
        self.assertTrue(totp.verify(secret, "287082", timestamp=59))
        self.assertFalse(totp.verify(secret, "000000", timestamp=59))

    def test_login_with_second_factor(self):
        from rest_framework.test import APIClient

        from users import totp

        user = make_user("payroll", User.Roles.PAYROLL_OFFICER)
        client = client_for(user)
        setup = client.get("/api/auth/2fa/setup/").json()
        self.assertTrue(setup["uri"].startswith("otpauth://totp/"))
        user.refresh_from_db()
        self.assertEqual(
            client.post("/api/auth/2fa/setup/", {"code": "000000"}).status_code, 400
        )
        self.assertEqual(
            client.post(
                "/api/auth/2fa/setup/", {"code": totp.code_at(user.totp_secret)}
            ).status_code,
            200,
        )

        anonymous = APIClient()
        first = anonymous.post(
            "/api/auth/login/", {"username": "payroll", "password": "Passw0rd!"}
        ).json()
        self.assertTrue(first["two_factor_required"])
        self.assertNotIn("access", first)
        bad = anonymous.post(
            "/api/auth/2fa/verify/", {"challenge": first["challenge"], "code": "000000"}
        )
        self.assertEqual(bad.status_code, 400)
        good = anonymous.post(
            "/api/auth/2fa/verify/",
            {"challenge": first["challenge"], "code": totp.code_at(user.totp_secret)},
        )
        self.assertIn("access", good.json())

    def test_admin_resets_second_factor(self):
        admin = make_user("admin", User.Roles.SYSTEM_ADMINISTRATOR)
        user = make_user("payroll", User.Roles.PAYROLL_OFFICER)
        user.totp_enabled, user.totp_secret = True, "ABC"
        user.save()
        client_for(admin).post(f"/api/users/management/{user.id}/reset_two_factor/")
        user.refresh_from_db()
        self.assertFalse(user.totp_enabled)


class SystemAdministratorAccessTests(TestCase):
    def test_system_administrator_accesses_everything(self):
        from users.permissions import ACTIONS, MODULES, has_module_permission

        admin = make_user("sysadmin_all", User.Roles.SYSTEM_ADMINISTRATOR)
        self.assertFalse(admin.is_superuser)
        for module in MODULES:
            for action in ACTIONS:
                self.assertTrue(has_module_permission(admin, module, action))
        client = client_for(admin)
        perms = client.get("/api/users/me/permissions/").json()
        self.assertTrue(perms["can_view_salary"])
        self.assertEqual(set(perms["permissions"]), set(MODULES))
        for url in (
            "/api/accounting/entries/",
            "/api/payroll/periods/",
            "/api/employees/",
            "/api/audit-logs/",
        ):
            self.assertEqual(client.get(url).status_code, 200, url)
