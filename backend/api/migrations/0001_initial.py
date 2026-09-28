# flake8: noqa
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="Site",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150, unique=True)),
                ("code", models.CharField(max_length=20, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                ("code", models.CharField(max_length=20)),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="departments",
                        to="api.site",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AlterUniqueTogether(
            name="department",
            unique_together={("site", "code")},
        ),
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150)),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="teams",
                        to="api.department",
                    ),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Designates that this user has all permissions without "
                            "explicitly assigning them."
                        ),
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text=(
                            "Required. 150 characters or fewer. Letters, digits and "
                            "@/./+/-/_ only."
                        ),
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True, max_length=254, verbose_name="email address"
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text=(
                            "Designates whether this user should be treated as active. "
                            "Unselect this instead of deleting accounts."
                        ),
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="date joined"
                    ),
                ),
                (
                    "employee_id",
                    models.CharField(blank=True, max_length=32, null=True, unique=True),
                ),
                ("is_payroll_authorized", models.BooleanField(default=False)),
                ("two_factor_enabled", models.BooleanField(default=False)),
                ("two_factor_secret", models.CharField(blank=True, max_length=64)),
                ("must_change_password", models.BooleanField(default=True)),
                ("password_changed_at", models.DateTimeField(blank=True, null=True)),
                ("password_history", models.JSONField(blank=True, default=list)),
                ("failed_login_attempts", models.PositiveIntegerField(default=0)),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("last_activity", models.DateTimeField(blank=True, null=True)),
                (
                    "processing_purpose",
                    models.TextField(
                        blank=True,
                        default=(
                            "Human resources management: payroll, leave, performance "
                            "and legal/regulatory compliance."
                        ),
                    ),
                ),
                ("data_retention_until", models.DateField(blank=True, null=True)),
                ("data_processing_consent", models.BooleanField(default=False)),
                ("consent_given_at", models.DateTimeField(blank=True, null=True)),
                (
                    "department",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="users",
                        to="api.department",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text=(
                            "The groups this user belongs to. A user will get all "
                            "permissions granted to each of their groups."
                        ),
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "manager",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="direct_reports",
                        to="api.user",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="users",
                        to="api.site",
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="users",
                        to="api.team",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "ordering": ["username"],
                "abstract": False,
            },
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "scope",
                    models.CharField(
                        choices=[
                            ("own", "Own data only"),
                            ("team", "Team"),
                            ("department", "Department"),
                            ("site", "Site"),
                            ("organisation", "Whole organisation"),
                        ],
                        default="own",
                        max_length=20,
                    ),
                ),
                ("requires_two_factor", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "module",
                    models.CharField(
                        choices=[
                            ("employees", "Employee records"),
                            ("payroll", "Payroll & compensation"),
                            ("leave", "Leave & absence"),
                            ("time_attendance", "Time & attendance"),
                            ("recruitment", "Recruitment"),
                            ("training", "Training & development"),
                            ("performance", "Performance management"),
                            ("documents", "Documents"),
                            ("admin", "Roles & security administration"),
                            ("audit", "Audit trail"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("consult", "Consult"),
                            ("create", "Create"),
                            ("modify", "Modify"),
                            ("validate", "Validate"),
                            ("print", "Print"),
                            ("export", "Export"),
                            ("delete", "Delete"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="permissions",
                        to="api.role",
                    ),
                ),
            ],
            options={"ordering": ["module", "action"]},
        ),
        migrations.AlterUniqueTogether(
            name="rolepermission",
            unique_together={("role", "module", "action")},
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="role_assignments_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="api.role",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-assigned_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="userrole",
            unique_together={("user", "role")},
        ),
        migrations.CreateModel(
            name="SalaryRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("base_salary", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("effective_date", models.DateField()),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="salary_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-effective_date"]},
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("username_snapshot", models.CharField(blank=True, max_length=150)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("create", "Creation"),
                            ("update", "Modification"),
                            ("delete", "Deletion"),
                            ("validate", "Validation"),
                            ("print", "Printing"),
                            ("export", "Export"),
                            ("login_success", "Successful login"),
                            ("login_failure", "Failed login attempt"),
                            ("logout", "Logout"),
                            ("password_change", "Password change"),
                            ("access_denied", "Access denied"),
                            ("session_expired", "Session expired (inactivity)"),
                            ("account_locked", "Account locked"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "module",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("employees", "Employee records"),
                            ("payroll", "Payroll & compensation"),
                            ("leave", "Leave & absence"),
                            ("time_attendance", "Time & attendance"),
                            ("recruitment", "Recruitment"),
                            ("training", "Training & development"),
                            ("performance", "Performance management"),
                            ("documents", "Documents"),
                            ("admin", "Roles & security administration"),
                            ("audit", "Audit trail"),
                        ],
                        max_length=32,
                    ),
                ),
                ("object_type", models.CharField(blank=True, max_length=100)),
                ("object_id", models.CharField(blank=True, max_length=64)),
                ("object_repr", models.CharField(blank=True, max_length=255)),
                ("previous_value", models.JSONField(blank=True, null=True)),
                ("new_value", models.JSONField(blank=True, null=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("machine", models.CharField(blank=True, max_length=255)),
                ("session_key", models.CharField(blank=True, max_length=40)),
                ("notes", models.CharField(blank=True, max_length=500)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-timestamp"]},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["-timestamp"], name="audit_timestamp_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["user", "action"], name="audit_user_action_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["module"], name="audit_module_idx"),
        ),
        migrations.CreateModel(
            name="DataSubjectRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "request_type",
                    models.CharField(
                        choices=[
                            ("access", "Right of access"),
                            ("rectification", "Right of rectification"),
                        ],
                        max_length=20,
                    ),
                ),
                ("details", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In progress"),
                            ("completed", "Completed"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("handled_at", models.DateTimeField(blank=True, null=True)),
                ("resolution_notes", models.TextField(blank=True)),
                (
                    "employee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="data_subject_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "handled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="handled_data_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-requested_at"]},
        ),
    ]
