import sys

import django
from django.apps import AppConfig


def _patch_context_copy_for_python_314():
    """
    Django 4.2 copies template contexts with copy(super()), which fails on
    Python 3.14 (fixed in Django 5.2). The CI runs Python 3.11 and is not
    affected; this keeps local development environments working.
    """
    from django.template.context import BaseContext

    def __copy__(self):
        duplicate = object.__new__(self.__class__)
        duplicate.__dict__ = self.__dict__.copy()
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = __copy__


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        if sys.version_info >= (3, 14) and django.VERSION < (5, 2):
            _patch_context_copy_for_python_314()
