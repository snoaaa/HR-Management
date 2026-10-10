from django.contrib import admin

from .models import (
    CareerAct,
    DepartmentVersion,
)

admin.site.register(CareerAct)
admin.site.register(DepartmentVersion)
