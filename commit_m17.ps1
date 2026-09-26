git add backend/hrms_backend/settings.py
git commit -m "setup custom user model"
git add backend/users/__init__.py backend/users/apps.py backend/users/models.py backend/users/tests.py backend/users/views.py
git commit -m "add user model and audit log structure"
git add backend/users/admin.py
git commit -m "register user and audit models in admin panel"
git add backend/users/utils.py
git commit -m "write utility for capturing audit logs"
git add backend/users/migrations/
git commit -m "makemigrations for users app"
git add backend/requirements.txt
git commit -m "add drf and simplejwt deps"
git add backend/api/urls.py
git commit -m "wire up the api routes for users and auth"
git add backend/api/serializers.py
git commit -m "create serializers for user and audit log"
git add backend/api/views.py
git commit -m "implement views for login, user management and audit trail"
git add frontend/package.json frontend/package-lock.json
git commit -m "install axios and jwt decode"
git add frontend/src/api/
git commit -m "setup axios interceptors"
git add frontend/src/context/AuthContext.tsx
git commit -m "implement auth context for global state"
git add frontend/src/components/auth/SignInForm.tsx
git commit -m "update sign in form to use auth context"
git add frontend/src/components/header/UserDropdown.tsx
git commit -m "hook up logout functionality"
git add frontend/src/components/auth/ChangePasswordForm.tsx frontend/src/pages/AuthPages/ChangePassword.tsx
git commit -m "build force password change flow"
git add frontend/src/components/auth/ProtectedRoute.tsx
git commit -m "add protected route wrapper"
git add frontend/src/components/common/Loader.tsx
git commit -m "add simple loader component"
git add frontend/src/layout/AppHeader.tsx
git commit -m "fix z-index issue with sticky header"
git add frontend/src/components/tables/UserTable.tsx
git commit -m "build user table component"
git add frontend/src/components/users/UserModal.tsx
git commit -m "create modal for adding and editing users"
git add frontend/src/pages/Users/UserManagement.tsx
git commit -m "assemble user management dashboard"
git add frontend/src/pages/Users/AuditTrail.tsx
git commit -m "build audit trail page with csv export"
git add frontend/src/layout/AppSidebar.tsx
git commit -m "add users and audit links to sidebar"
git add frontend/src/components/UserProfile/UserMetaCard.tsx
git commit -m "make user profile card dynamic"
git add frontend/src/App.tsx
git commit -m "register all new routes in app"
