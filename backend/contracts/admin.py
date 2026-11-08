from django.contrib import admin

from .models import (
    Contract,
    ContractAmendment,
    ContractRenewal,
    ContractSuspension,
    ContractTermination,
)

admin.site.register(Contract)
admin.site.register(ContractAmendment)
admin.site.register(ContractRenewal)
admin.site.register(ContractSuspension)
admin.site.register(ContractTermination)
