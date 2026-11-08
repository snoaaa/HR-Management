from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"parameters", views.ParameterViewSet, basename="payroll-parameter")
router.register(r"scales", views.ScaleViewSet, basename="payroll-scale")
router.register(
    r"deductions", views.StatutoryDeductionViewSet, basename="statutory-deduction"
)
router.register(r"elements", views.SalaryElementViewSet, basename="salary-element")
router.register(r"element-values", views.ElementValueViewSet, basename="element-value")
router.register(r"grid", views.SalaryGridViewSet, basename="salary-grid")
router.register(r"history", views.ParameterChangeViewSet, basename="parameter-change")
router.register(r"periods", views.PeriodViewSet, basename="payroll-period")
router.register(r"payslips", views.PayslipViewSet, basename="payslip")
router.register(r"inputs", views.VariableInputViewSet, basename="variable-input")
router.register(r"loans", views.LoanViewSet, basename="loan")
router.register(
    r"third-party", views.ThirdPartyDeductionViewSet, basename="third-party-deduction"
)

urlpatterns = [
    path(
        "annual-statement/",
        views.AnnualStatementView.as_view(),
        name="annual-statement",
    ),
    path("annual-summary/", views.AnnualSummaryView.as_view(), name="annual-summary"),
    path("simulate/", views.SimulationView.as_view(), name="payroll-simulate"),
    path(
        "final-settlement/<int:termination_id>/",
        views.FinalSettlementView.as_view(),
        name="final-settlement",
    ),
    path("", include(router.urls)),
]
