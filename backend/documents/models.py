from django.conf import settings
from django.db import models


class DocumentTemplate(models.Model):
    """
    BN-35 / BN-124 / BN-125: configurable template of a printed document.
    The body uses the Django template syntax ({{ employee.surname }} ...).
    The organisation header (logo, legal identification) is added
    automatically to every document.
    """

    CATEGORIES = (
        ("CONTRACT", "Contract"),
        ("CERTIFICATE", "Certificate / attestation"),
        ("LEAVE", "Leave"),
        ("PAYROLL", "Payroll"),
        ("DECISION", "Decision"),
        ("OTHER", "Other"),
    )

    code = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=CATEGORIES, default="OTHER")
    body = models.TextField(help_text="HTML with Django template variables.")
    footer = models.CharField(max_length=255, blank=True)
    signature_block = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class IssuedDocument(models.Model):
    """BN-127: copy of every document issued, with date, author and recipient."""

    template_code = models.CharField(max_length=60)
    title = models.CharField(max_length=255)
    reference = models.CharField(max_length=60, blank=True)
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="issued_documents",
    )
    recipient = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to="issued_documents/%Y/%m/")
    is_duplicate = models.BooleanField(default=False)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return self.title


class DocumentRequest(models.Model):
    """BN-152: an employee asks for an attestation and is told when it is ready."""

    STATUSES = (("PENDING", "Pending"), ("ISSUED", "Issued"), ("REFUSED", "Refused"))

    employee = models.ForeignKey(
        "employees.Employee", on_delete=models.CASCADE, related_name="document_requests"
    )
    template_code = models.CharField(max_length=60)
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUSES, default="PENDING")
    issued_document = models.ForeignKey(
        IssuedDocument, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
