from django.contrib import admin

from .models import (
    EmployeeSkill,
    Participation,
    PositionSkill,
    Skill,
    TrainingNeed,
    TrainingPlan,
    TrainingSession,
)

admin.site.register(EmployeeSkill)
admin.site.register(Participation)
admin.site.register(PositionSkill)
admin.site.register(Skill)
admin.site.register(TrainingNeed)
admin.site.register(TrainingPlan)
admin.site.register(TrainingSession)
