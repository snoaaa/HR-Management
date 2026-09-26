from rest_framework import serializers
from .models import CompanyIdentity, Site, CostCentre, Department, Classification, Position

class CompanyIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyIdentity
        fields = '__all__'

class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = '__all__'

class CostCentreSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCentre
        fields = '__all__'

class DepartmentSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    site_name = serializers.CharField(source='site.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    cost_centre_name = serializers.CharField(source='cost_centre.name', read_only=True)

    class Meta:
        model = Department
        fields = '__all__'

class ClassificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classification
        fields = '__all__'

class PositionSerializer(serializers.ModelSerializer):
    classification_details = ClassificationSerializer(source='classification', read_only=True)
    reporting_position_title = serializers.CharField(source='reporting_position.title', read_only=True)

    class Meta:
        model = Position
        fields = '__all__'
