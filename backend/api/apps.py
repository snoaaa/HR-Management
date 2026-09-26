from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"
    # Cherche la classe AppConfig existante et ajoute la méthode ready() :
#
# class ApiConfig(AppConfig):
#     default_auto_field = "django.db.models.BigAutoField"
#     name = "api"
#
#     def ready(self):
#         from . import signals  # noqa: F401  (connecte les signaux login/logout)