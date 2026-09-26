from django.contrib import admin
from .models import CompanyIdentity, Site, CostCentre, Department, Classification, Position

@admin.register(CompanyIdentity)
class CompanyIdentityAdmin(admin.ModelAdmin):
    list_display = ('corporate_name', 'registration_number', 'tax_id')

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(CostCentre)
class CostCentreAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'unit_type', 'parent', 'site', 'manager')
    list_filter = ('unit_type', 'site')
    search_fields = ('name', 'code')

@admin.register(Classification)
class ClassificationAdmin(admin.ModelAdmin):
    list_display = ('category', 'grade', 'echelon', 'coefficient')
    list_filter = ('category',)

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'code', 'classification', 'reporting_position')
    search_fields = ('title', 'code')
    list_filter = ('classification',)
