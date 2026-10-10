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
