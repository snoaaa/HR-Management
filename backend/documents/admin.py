from django.contrib import admin

from .models import (
    DocumentRequest,
    DocumentTemplate,
    IssuedDocument,
)

admin.site.register(DocumentRequest)
admin.site.register(DocumentTemplate)
admin.site.register(IssuedDocument)
