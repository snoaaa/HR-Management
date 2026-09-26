from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmployeeViewSet, FamilyMemberViewSet, EmployeeDocumentViewSet,
    EducationAndExperienceViewSet, EmployeeHistoryViewSet
)

router = DefaultRouter()
router.register(r'', EmployeeViewSet, basename='employee')

# For nested routes without drf-nested-routers
family_member_list = FamilyMemberViewSet.as_view({'get': 'list', 'post': 'create'})
family_member_detail = FamilyMemberViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

document_list = EmployeeDocumentViewSet.as_view({'get': 'list', 'post': 'create'})
document_detail = EmployeeDocumentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

education_list = EducationAndExperienceViewSet.as_view({'get': 'list', 'post': 'create'})
education_detail = EducationAndExperienceViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'})

history_list = EmployeeHistoryViewSet.as_view({'get': 'list'})
history_detail = EmployeeHistoryViewSet.as_view({'get': 'retrieve'})

urlpatterns = [
    path('<int:employee_pk>/family-members/', family_member_list, name='family-member-list'),
    path('<int:employee_pk>/family-members/<int:pk>/', family_member_detail, name='family-member-detail'),
    
    path('<int:employee_pk>/documents/', document_list, name='document-list'),
    path('<int:employee_pk>/documents/<int:pk>/', document_detail, name='document-detail'),
    
    path('<int:employee_pk>/education/', education_list, name='education-list'),
    path('<int:employee_pk>/education/<int:pk>/', education_detail, name='education-detail'),
    
    path('<int:employee_pk>/history/', history_list, name='history-list'),
    path('<int:employee_pk>/history/<int:pk>/', history_detail, name='history-detail'),
    
    path('', include(router.urls)),
]
