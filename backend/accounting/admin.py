from django.contrib import admin

from .models import (
    Account,
    AccountMapping,
    AccountingPeriod,
    Budget,
    FiscalYear,
    Journal,
    JournalEntry,
    JournalLine,
)

admin.site.register(Account)
admin.site.register(AccountMapping)
admin.site.register(AccountingPeriod)
admin.site.register(Budget)
admin.site.register(FiscalYear)
admin.site.register(Journal)
admin.site.register(JournalEntry)
admin.site.register(JournalLine)
