from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Employee, FamilyMember, EmployeeDocument, EducationAndExperience, EmployeeHistory
from .serializers import (
    EmployeeSerializer, FamilyMemberSerializer, EmployeeDocumentSerializer, 
    EducationAndExperienceSerializer, EmployeeHistorySerializer
)
from rest_framework.permissions import IsAuthenticated

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Employee. Includes search, filter and custom actions.
    """
    queryset = Employee.objects.all().order_by('-id')
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # BN-19: Search and filter employees on any criterion
    filterset_fields = ['department', 'position', 'contract_type', 'status', 'workplace']
    search_fields = ['surname', 'given_names', 'matriculation_number', 'personal_email']
    ordering_fields = ['surname', 'date_of_hire', 'matriculation_number']

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """
        BN-09: Archive an employee record without physically deleting it.
        """
        employee = self.get_object()
        employee.status = 'ARCHIVED'
        employee.save()
        
        # BN-21: Log the modification
        EmployeeHistory.objects.create(
            employee=employee,
            author=request.user,
            field_name='status',
            previous_value='ACTIVE/INACTIVE',
            new_value='ARCHIVED'
        )
        return Response({'status': 'employee archived'}, status=status.HTTP_200_OK)


class FamilyMemberViewSet(viewsets.ModelViewSet):
    serializer_class = FamilyMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FamilyMember.objects.filter(employee_id=self.kwargs['employee_pk'])

    def perform_create(self, serializer):
        serializer.save(employee_id=self.kwargs['employee_pk'])


class EmployeeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = EmployeeDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeDocument.objects.filter(employee_id=self.kwargs['employee_pk'])

    def perform_create(self, serializer):
        serializer.save(employee_id=self.kwargs['employee_pk'])


class EducationAndExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = EducationAndExperienceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EducationAndExperience.objects.filter(employee_id=self.kwargs['employee_pk'])

    def perform_create(self, serializer):
        serializer.save(employee_id=self.kwargs['employee_pk'])


class EmployeeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmployeeHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EmployeeHistory.objects.filter(employee_id=self.kwargs['employee_pk']).order_by('-modification_date')
