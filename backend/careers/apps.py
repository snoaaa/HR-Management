from django.apps import AppConfig


class CareersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "careers"

    def ready(self):
        from django.db.models.signals import post_save, pre_delete

        from organisation.models import Department

        def on_save(sender, instance, **kwargs):
            from .services import record_department_version

            record_department_version(instance)

        def on_delete(sender, instance, **kwargs):
            from .services import record_department_version

            record_department_version(instance, deleted=True)

        # BN-06: every modification of the structure is historised.
        post_save.connect(
            on_save, sender=Department, dispatch_uid="careers-department-version"
        )
        pre_delete.connect(
            on_delete, sender=Department, dispatch_uid="careers-department-delete"
        )
