from django.contrib import admin

from .models import (
    BackPayAdjustment,
    ElementValue,
    LeaveProvision,
    Loan,
    LoanRepayment,
    ParameterChange,
    PayrollParameter,
    PayrollPeriod,
    Payslip,
    PayslipLine,
    PeriodTransition,
    SalaryElement,
    SalaryGrid,
    Scale,
    StatutoryDeduction,
    ThirdPartyDeduction,
    ThirdPartyRepayment,
    VariableInput,
)

admin.site.register(BackPayAdjustment)
admin.site.register(ElementValue)
admin.site.register(LeaveProvision)
admin.site.register(Loan)
admin.site.register(LoanRepayment)
admin.site.register(ParameterChange)
admin.site.register(PayrollParameter)
admin.site.register(PayrollPeriod)
admin.site.register(Payslip)
admin.site.register(PayslipLine)
admin.site.register(PeriodTransition)
admin.site.register(SalaryElement)
admin.site.register(SalaryGrid)
admin.site.register(Scale)
admin.site.register(StatutoryDeduction)
admin.site.register(ThirdPartyDeduction)
admin.site.register(ThirdPartyRepayment)
admin.site.register(VariableInput)
