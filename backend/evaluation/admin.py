from django.contrib import admin

from .models import (
    Campaign,
    Evaluation,
    Objective,
)

admin.site.register(Campaign)
admin.site.register(Evaluation)
admin.site.register(Objective)
