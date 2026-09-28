# M-17 — Security, Roles and Audit

This document maps each business need from section 7.17 of the
Expression of Need to the code that implements it, and explains how to
try it out locally.

| Ref | Need | Where it's implemented |
|-----|------|-------------------------|
| BN-169 | Individual authentication, no shared accounts | `api.models.User` (custom, `AUTH_USER_MODEL`), `api.views.LoginView` |
| BN-170 | Fine-grained permissions per module/action | `api.models.Module`, `Action`, `Role`, `RolePermission`; `api.permissions.HasModulePermission` |
| BN-171 | Visibility perimeter (own/team/department/site/org) | `api.models.Scope`, `Site`/`Department`/`Team`, `Role.scope`, `User.broadest_scope()`, `api.permissions.ScopedQuerysetMixin` |
| BN-172 | Salary data restricted to explicitly authorised profiles | `api.models.SalaryRecord`, `User.is_payroll_authorized`, `api.permissions.SalaryConfidentiality` |
| BN-173 | Immutable audit trail (author, date, machine, previous value) | `api.models.AuditLog`, `api.services.record_audit`, `api.signals` (auto-audits `SalaryRecord`/`UserRole` + login/logout events), `api.middleware.AuditContextMiddleware` |
| BN-174 | Password policy, forced change at first login, idle session timeout | `api.validators.PasswordComplexityValidator` / `PasswordHistoryValidator`, `User.must_change_password`, `api.middleware.ForcePasswordChangeMiddleware`, `api.middleware.SessionTimeoutMiddleware` |
| BN-175 | Audit trail can be consulted/exported but never altered/deleted | `AuditLog.save()`/`delete()` (raise `PermissionDenied`), `api.views.AuditLogViewSet` (`ReadOnlyModelViewSet` + `/export`), `api.admin.AuditLogAdmin` (add/change/delete disabled) |
| BN-176 | Second factor for payroll profiles | `User.two_factor_enabled/secret`, `Role.requires_two_factor`, `api.views.TwoFactorSetupView`/`TwoFactorVerifyView`, `api.permissions.TwoFactorRequired` |
| BN-177 | GDPR-style purpose/minimisation/retention/consult/rectify | `User.processing_purpose`, `data_retention_until`, `data_processing_consent`; `api.models.DataSubjectRequest`; `api.views.DataSubjectRequestViewSet` |

## How the pieces fit together

- **Roles** (`Role`) carry a list of `(module, action)` grants
  (`RolePermission`) plus a single visibility `scope`. A user can hold
  several roles (`UserRole`); permission checks OR across all of them,
  and the *widest* scope granted for a given module/action wins.
- Every `ModelViewSet` that touches HRMS data sets a `module` attribute
  and uses `HasModulePermission`, which maps the DRF action (`list`,
  `create`, `update`, ...) or a custom `@action` name (`export`,
  `print`, `resolve`, ...) onto one of the seven actions from BN-170.
  A denied check is itself written to the audit trail.
- **Salary data** goes through an extra gate on top of the module
  check: the account needs `is_payroll_authorized=True` (BN-172), and
  if a role or that flag requires it, the current session must have
  passed 2FA verification (BN-176).
- The **audit trail** is populated two ways: automatically via Django
  signals for the models listed in `api.signals.AUDITED_MODELS` (salary
  records, role assignments) and login/logout/failed-login events, and
  explicitly via `api.services.record_audit(...)` wherever a view needs
  to log something signals can't see (role/user CRUD, exports, GDPR
  request resolution). Once written, an entry cannot be changed or
  removed — enforced in the model itself, not just in the API.
- **Password policy**: `AUTH_PASSWORD_VALIDATORS` in `settings.py` runs
  Django's stock checks (length, similarity, common passwords, not
  fully numeric) plus a complexity rule and a 5-password history rule.
  New accounts are created with `must_change_password=True`; the
  `ForcePasswordChangeMiddleware` blocks every other endpoint until
  `POST /api/auth/password/change/` succeeds.
- **Session timeout**: `SessionTimeoutMiddleware` logs a user out (401)
  once `SESSION_INACTIVITY_TIMEOUT_MINUTES` (default 30) has passed
  with no request; `SESSION_COOKIE_AGE` (default 8h) is a hard ceiling
  regardless of activity.

## Trying it out

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_security   # optional: creates a starter set of roles
python manage.py runserver
```

Typical flow against the API:

1. `POST /api/auth/login/` with `{"username": ..., "password": ...}`.
2. If `must_change_password` comes back `true`, call
   `POST /api/auth/password/change/` before anything else will work.
3. As an account holding the ADMIN-module permission, create `Role`s and
   `RolePermission`s (`/api/roles/`), then assign them to users
   (`/api/user-roles/`).
4. Consult the trail at `/api/audit-log/` (filterable by
   `?action=`, `?module=`, `?user=`, `?date_from=`, `?date_to=`) or
   export it as CSV from `/api/audit-log/export/`.

Automated coverage lives in `backend/api/tests.py`, one `TestCase` per
business need (`BN169IndividualAuthenticationTests`,
`BN170FineGrainedPermissionTests`, ... `BN177GDPRTests`) — run it with
`python manage.py test`.

## Notes / follow-ups for a production rollout

- `two_factor_secret` is currently stored in clear text for simplicity;
  before going live it should be encrypted at rest (e.g. via
  `django-fernet-fields` or an application-level KMS call).
- Account lockout (5 failed attempts / 15 minutes, see
  `api.signals.MAX_FAILED_ATTEMPTS` / `LOCKOUT_MINUTES`) and the idle
  timeout are deliberately conservative defaults — tune them to the
  organisation's actual security policy.
- `DataSubjectRequest` models the *workflow* (request → resolution) for
  BN-177; wiring it up to an actual data export/rectification
  procedure for a given employee is a separate, module-specific task.
- This implementation was written and syntax-checked in an environment
  without network access to install Django itself, so it could not be
  exercised end-to-end with `python manage.py test` before delivery.
  Every cross-file reference (models, signals, permissions, serializers,
  views, urls) was checked by hand for consistency, and the code follows
  the pre-existing `migrations/0001_initial.py` field-for-field, but
  please run the test suite and `black backend/` (to normalise formatting
  for the CI's `black --check`) as the first step after pulling this in.
