from django.contrib import admin

from .models import (
    Application,
    ApplicationEvent,
    JobOffer,
    OnboardingTask,
    RecruitmentNeed,
)

admin.site.register(Application)
admin.site.register(ApplicationEvent)
admin.site.register(JobOffer)
admin.site.register(OnboardingTask)
admin.site.register(RecruitmentNeed)
