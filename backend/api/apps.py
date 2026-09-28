from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        # Registers the signal receivers that power BN-173's automatic
        # audit trail (model changes + login/logout/lockout events).
        from . import signals  # noqa: F401
