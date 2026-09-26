from django.db import models
from django.conf import settings

class CompanyIdentity(models.Model):
    """
    BN-01: Register the identity of the organisation.
    Typically a single row table for the company.
    """
    corporate_name = models.CharField(max_length=255)
    legal_form = models.CharField(max_length=100)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    social_insurance_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField()
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    legal_representative = models.CharField(max_length=255)

    def __str__(self):
        return self.corporate_name
        
    class Meta:
        verbose_name = "Company Identity"
        verbose_name_plural = "Company Identities"


class Site(models.Model):
    """
    BN-02, BN-08: Manage several sites with different working calendars and holidays.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class CostCentre(models.Model):
    """
    BN-05: Attach every organisational unit to a cost centre used later by accounting.
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Department(models.Model):
    """
    BN-02: Manage a hierarchy of organisational units on several levels: company, site or establishment, division, department, service, and team.
    BN-05: Attach every organisational unit to a manager and to a cost centre.
    """
    UNIT_TYPES = (
        ('COMPANY', 'Company'),
        ('SITE', 'Site/Establishment'),
        ('DIVISION', 'Division'),
        ('DEPARTMENT', 'Department'),
        ('SERVICE', 'Service'),
        ('TEAM', 'Team'),
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    unit_type = models.CharField(max_length=20, choices=UNIT_TYPES, default='DEPARTMENT')
    
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='sub_units')
    site = models.ForeignKey(Site, on_delete=models.SET_NULL, blank=True, null=True, related_name='departments')
    manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='managed_departments')
    cost_centre = models.ForeignKey(CostCentre, on_delete=models.SET_NULL, blank=True, null=True, related_name='departments')

    def __str__(self):
        return f"{self.name} - {self.get_unit_type_display()}"


class Classification(models.Model):
    """
    BN-04: Manage the grid of professional categories, grades, echelons and coefficients used for classification and for the base salary.
    """
    category = models.CharField(max_length=50, help_text="e.g. Executive, Supervisor, Employee")
    grade = models.CharField(max_length=50)
    echelon = models.CharField(max_length=50, blank=True, null=True)
    coefficient = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.category} - {self.grade}{' - ' + self.echelon if self.echelon else ''}"
        
    class Meta:
        unique_together = ('category', 'grade', 'echelon')


class Position(models.Model):
    """
    BN-03: Manage the catalogue of positions with their title, mission, required skills, salary category and reporting position.
    """
    title = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    mission = models.TextField(blank=True, null=True)
    required_skills = models.TextField(blank=True, null=True)
    classification = models.ForeignKey(Classification, on_delete=models.SET_NULL, blank=True, null=True, related_name='positions')
    reporting_position = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='direct_reports')

    def __str__(self):
        return self.title
