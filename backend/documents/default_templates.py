"""
Default document templates. They are copied into the DocumentTemplate table
and can then be modified by the organisation without development (BN-125).

code: (name, category, body, footer)
"""

SIGNATURES = """
<br/><table class="signature"><tr>
<td width="50%"><b>The employee</b><br/>{{ employee.full_name }}<br/>(read and approved)</td>
<td width="50%"><b>For the employer</b><br/>{{ company.legal_representative|default:"" }}{% if company.legal_representative_title %}, {{ company.legal_representative_title }}{% endif %}</td>
</tr></table>
"""

EMPLOYEE_BLOCK = """
<table class="no-border">
<tr><td width="35%">Name</td><td><b>{{ employee.surname }} {{ employee.given_names }}</b></td></tr>
<tr><td>Matriculation</td><td>{{ employee.matriculation_number }}</td></tr>
<tr><td>Born on</td><td>{{ employee.date_of_birth|date:"d/m/Y" }} at {{ employee.place_of_birth }}</td></tr>
<tr><td>Nationality</td><td>{{ employee.nationality }}</td></tr>
<tr><td>Identity document</td><td>{{ employee.identity_document_type }} n° {{ employee.identity_document_number }}</td></tr>
<tr><td>Address</td><td>{{ employee.address }}</td></tr>
</table>
"""

CONTRACT = (
    "Employment contract",
    "CONTRACT",
    """
<h1>{{ contract.get_contract_type_display|upper }}</h1>
<p class="muted">Reference: {{ contract.reference }}</p>
<p>Between <b>{{ company.corporate_name }}</b>, {{ company.legal_form }}, {{ company.address }},
represented by {{ company.legal_representative }}, hereafter "the employer",</p>
<p>and the employee:</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>it is agreed as follows.</p>
<h2>Article 1 – Engagement</h2>
<p>The employee is engaged as <b>{{ contract.position.title|default:"" }}</b>
{% if contract.classification %}(category {{ contract.classification }}){% endif %}
from <b>{{ contract.start_date|date:"d/m/Y" }}</b>
{% if contract.end_date %}until <b>{{ contract.end_date|date:"d/m/Y" }}</b>{% else %}for an indefinite period{% endif %}.</p>
<h2>Article 2 – Trial period</h2>
<p>{% if contract.trial_period_end %}The contract includes a trial period ending on
{{ contract.trial_period_end|date:"d/m/Y" }}.{% else %}The contract has no trial period.{% endif %}</p>
<h2>Article 3 – Place and working time</h2>
<p>The employee works at {{ contract.workplace.name|default:"the registered office" }},
{{ contract.weekly_hours }} hours per week.</p>
<h2>Article 4 – Remuneration</h2>
<p>The employee receives a monthly base salary of <b>{{ contract.base_salary|money }} {{ currency }}</b>,
plus the allowances provided for by the collective agreement and the internal rules.</p>
<h2>Article 5 – Notice</h2>
<p>Either party may end the contract with a notice of {{ contract.notice_period_days }} days,
under the conditions of the Labour Code.</p>
<p>Done at {{ company.address|default:"" }}, on {{ today|date:"d/m/Y" }}, in two originals.</p>
"""
    + SIGNATURES,
    "Employment contract",
)

AMENDMENT = (
    "Contract amendment",
    "CONTRACT",
    """
<h1>AMENDMENT N° {{ amendment.version }} TO THE EMPLOYMENT CONTRACT</h1>
<p class="muted">Contract {{ contract.reference }} – Reference {{ reference }}</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>The parties agree to amend the employment contract as follows, with effect from
<b>{{ amendment.effective_date|date:"d/m/Y" }}</b>:</p>
<table><thead><tr><th>Item</th><th>Previous value</th><th>New value</th></tr></thead><tbody>
{% for change in changes %}<tr><td>{{ change.label }}</td><td>{{ change.old }}</td><td>{{ change.new }}</td></tr>{% endfor %}
</tbody></table>
<p>Reason: {{ amendment.reason }}</p>
<p>All the other clauses of the contract remain unchanged.</p>
"""
    + SIGNATURES,
    "Contract amendment",
)

WORK_CERTIFICATE = (
    "Work certificate",
    "CERTIFICATE",
    """
<h1>WORK CERTIFICATE</h1>
<p class="muted">Reference {{ reference }}</p>
<p>I, the undersigned, {{ company.legal_representative }}, acting for {{ company.corporate_name }},
certify that</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>was employed by our organisation from <b>{{ start_date|date:"d/m/Y" }}</b>
to <b>{{ end_date|date:"d/m/Y" }}</b>, as <b>{{ position }}</b>.</p>
<p>{{ employee.given_names }} {{ employee.surname }} leaves the organisation free of any commitment.</p>
<p>This certificate is issued to serve and be used as required by law.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p>
<br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
""",
    "Work certificate",
)

END_OF_CONTRACT = (
    "End-of-contract certificate",
    "CERTIFICATE",
    """
<h1>END-OF-CONTRACT CERTIFICATE</h1>
<p class="muted">Reference {{ reference }}</p>
"""
    + EMPLOYEE_BLOCK
    + """
<table class="no-border">
<tr><td width="35%">Contract</td><td>{{ contract.reference }} – {{ contract.get_contract_type_display }}</td></tr>
<tr><td>Start date</td><td>{{ contract.start_date|date:"d/m/Y" }}</td></tr>
<tr><td>Notified on</td><td>{{ termination.notification_date|date:"d/m/Y" }}</td></tr>
<tr><td>Last working day</td><td>{{ termination.termination_date|date:"d/m/Y" }}</td></tr>
<tr><td>Reason</td><td>{{ termination.get_reason_display }}</td></tr>
<tr><td>Notice</td><td>{{ termination.notice_days }} days{% if termination.notice_worked %} (worked){% else %} (not worked){% endif %}</td></tr>
<tr><td>Remaining leave</td><td>{{ termination.leave_balance_days }} days</td></tr>
</table>
<p>The final settlement of accounts is established separately by the payroll department.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p>
"""
    + SIGNATURES,
    "End-of-contract certificate",
)

LEAVE_DECISION = (
    "Leave decision",
    "LEAVE",
    """
<h1>LEAVE DECISION</h1>
<p class="muted">Reference {{ reference }}</p>
<p>The management of {{ company.corporate_name }} grants to</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>a <b>{{ leave.leave_type.name|lower }}</b> of <b>{{ leave.days }} day(s)</b>
from <b>{{ leave.start_date|date:"d/m/Y" }}</b> to <b>{{ leave.end_date|date:"d/m/Y" }}</b>
inclusive.</p>
{% if leave.replacement %}<p>During this absence, the employee is replaced by
{{ leave.replacement.full_name }}.</p>{% endif %}
<p>The employee will resume work on the first working day following the end of the leave.</p>
<p>Remaining balance after this leave: {{ balance.remaining }} day(s).</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p>
<br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
""",
    "Leave decision",
)

LEAVE_CERTIFICATE = (
    "Leave certificate",
    "LEAVE",
    """
<h1>LEAVE CERTIFICATE</h1>
<p class="muted">Reference {{ reference }}</p>
<p>We certify that</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>is on <b>{{ leave.leave_type.name|lower }}</b> from {{ leave.start_date|date:"d/m/Y" }}
to {{ leave.effective_end_date|date:"d/m/Y" }} ({{ leave.days }} day(s)).</p>
<p>This certificate is issued to serve and be used as required.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p>
<br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
""",
    "Leave certificate",
)

LEAVE_BALANCE = (
    "Leave balance summary",
    "LEAVE",
    """
<h1>LEAVE BALANCE {{ year }}</h1>
"""
    + EMPLOYEE_BLOCK
    + """
<table>
<tr><th>Carried over</th><th>Acquired</th><th>Taken</th><th>Pending</th><th>Remaining</th></tr>
<tr><td class="num">{{ balance.carried_over }}</td><td class="num">{{ balance.acquired }}</td>
<td class="num">{{ balance.taken }}</td><td class="num">{{ balance.pending }}</td>
<td class="num"><b>{{ balance.remaining }}</b></td></tr>
</table>
<h2>Leaves of the year</h2>
<table><thead><tr><th>Type</th><th>From</th><th>To</th><th class="num">Days</th></tr></thead><tbody>
{% for leave in leaves %}<tr><td>{{ leave.leave_type.name }}</td><td>{{ leave.start_date|date:"d/m/Y" }}</td>
<td>{{ leave.effective_end_date|date:"d/m/Y" }}</td><td class="num">{{ leave.days }}</td></tr>
{% empty %}<tr><td colspan="4">No leave taken.</td></tr>{% endfor %}
</tbody></table>
<p class="muted">Situation on {{ today|date:"d/m/Y" }}.</p>
""",
    "Leave balance",
)

PAYSLIP = (
    "Payslip",
    "PAYROLL",
    """
<div style="font-size:8pt"><h1>PAYSLIP – {{ period.month|stringformat:"02d" }}/{{ period.year }}</h1>
<table class="no-border">
<tr><td width="50%">
<b>{{ employee.surname }} {{ employee.given_names }}</b><br/>
Matriculation: {{ employee.matriculation_number }}<br/>
Position: {{ payslip.contract.position.title|default:employee.position.title|default:"" }}<br/>
Category: {{ classification|default:"" }}<br/>
Hired on: {{ employee.date_of_hire|date:"d/m/Y" }} – seniority {{ seniority }} year(s)
</td><td width="50%">
CNPS n°: {{ employee.social_insurance_number|default:"—" }}<br/>
NIU: {{ employee.tax_identification_number|default:"—" }}<br/>
Department: {{ employee.department.name|default:"" }}<br/>
Period: {{ period.start_date|date:"d/m/Y" }} – {{ period.end_date|date:"d/m/Y" }}<br/>
Days paid: {{ payslip.paid_days }} – Working time: {{ weekly_hours }} h/week
</td></tr></table>
<table>
<thead><tr><th width="12%">Code</th><th width="24%">Item</th><th class="num" width="12%">Base</th><th class="num" width="9%">Qty / rate</th>
<th class="num" width="11%">Gain</th><th class="num" width="11%">Deduction</th><th class="num" width="9%">Empl. rate</th><th class="num" width="12%">Employer</th></tr></thead>
<tbody>
{% for line in lines %}<tr>
<td>{{ line.code }}</td><td>{{ line.label }}</td>
<td class="num">{{ line.base|money }}</td>
<td class="num">{% if line.quantity %}{{ line.quantity|floatformat:2 }}{% elif line.rate %}{{ line.rate|floatformat:2 }}%{% endif %}</td>
<td class="num">{% if line.is_gain %}{{ line.amount|money }}{% endif %}</td>
<td class="num">{% if not line.is_gain %}{{ line.amount|nonzero_money }}{% endif %}</td>
<td class="num">{% if line.employer_rate %}{{ line.employer_rate|floatformat:2 }}%{% endif %}</td>
<td class="num">{% if line.employer_amount %}{{ line.employer_amount|money }}{% endif %}</td>
</tr>{% endfor %}
</tbody></table>
<table>
<tr class="total"><td>Gross salary</td><td class="num">{{ payslip.gross|money }}</td>
<td>Contributory base</td><td class="num">{{ payslip.contributory_base|money }}</td>
<td>Taxable base</td><td class="num">{{ payslip.taxable_base|money }}</td></tr>
<tr><td>Employee contributions</td><td class="num">{{ payslip.employee_contributions|money }}</td>
<td>Taxes withheld</td><td class="num">{{ payslip.taxes|money }}</td>
<td>Other deductions</td><td class="num">{{ payslip.other_deductions|money }}</td></tr>
<tr><td>Employer contributions</td><td class="num">{{ payslip.employer_contributions|money }}</td>
<td>Benefits in kind</td><td class="num">{{ payslip.benefits_in_kind|money }}</td>
<td><b>NET PAYABLE ({{ currency }})</b></td><td class="num"><b>{{ payslip.net_payable|money }}</b></td></tr>
</table>
<p>Payment: {{ payslip.get_payment_method_display }}{% if payslip.bank_name %} – {{ payslip.bank_name }} {{ payslip.bank_account }}{% endif %}
– date: {{ period.payment_date|date:"d/m/Y"|default:"to be paid" }}.<br/>
Leave balance at the end of the period: {{ payslip.leave_balance|default_if_none:"—" }} day(s).</p>
<p class="muted">Keep this payslip without limit of time.</p></div>
""",
    "Payslip",
)

PAYROLL_BOOK = (
    "Payroll book",
    "PAYROLL",
    """
<h1>PAYROLL BOOK – {{ period.month|stringformat:"02d" }}/{{ period.year }}</h1>
{% for group in groups %}
<h2>{{ group.name }}</h2>
<table><thead><tr><th>Matric.</th><th>Employee</th><th class="num">Base</th><th class="num">Gross</th>
<th class="num">Emp. contrib.</th><th class="num">Taxes</th><th class="num">Other ded.</th>
<th class="num">Net payable</th><th class="num">Employer</th></tr></thead><tbody>
{% for p in group.payslips %}<tr><td>{{ p.employee.matriculation_number }}</td><td>{{ p.employee.full_name }}</td>
<td class="num">{{ p.base_salary|money }}</td><td class="num">{{ p.gross|money }}</td><td class="num">{{ p.employee_contributions|money }}</td>
<td class="num">{{ p.taxes|money }}</td><td class="num">{{ p.other_deductions|money }}</td><td class="num">{{ p.net_payable|money }}</td>
<td class="num">{{ p.employer_contributions|money }}</td></tr>{% endfor %}
<tr class="total"><td colspan="2">Total {{ group.name }}</td><td class="num">{{ group.totals.base_salary|money }}</td>
<td class="num">{{ group.totals.gross|money }}</td><td class="num">{{ group.totals.employee_contributions|money }}</td>
<td class="num">{{ group.totals.taxes|money }}</td><td class="num">{{ group.totals.other_deductions|money }}</td>
<td class="num">{{ group.totals.net_payable|money }}</td><td class="num">{{ group.totals.employer_contributions|money }}</td></tr>
</tbody></table>
{% endfor %}
<h2>Organisation total</h2>
<table><tr class="total"><td>Employees: {{ totals.count }}</td><td>Gross: {{ totals.gross|money }}</td>
<td>Net payable: {{ totals.net_payable|money }}</td><td>Employer charges: {{ totals.employer_contributions|money }}</td>
<td>Total cost: {{ totals.cost|money }}</td></tr></table>
""",
    "Payroll book",
)

CONTRIBUTION_STATEMENT = (
    "Statement of contributions and taxes",
    "PAYROLL",
    """
<h1>STATEMENT OF CONTRIBUTIONS AND TAXES WITHHELD – {{ period.month|stringformat:"02d" }}/{{ period.year }}</h1>
{% for body in bodies %}
<h2>{{ body.label }} – due on {{ body.due_date|date:"d/m/Y" }}</h2>
<table><thead><tr><th>Item</th><th class="num">Base</th><th class="num">Employee</th><th class="num">Employer</th>
<th class="num">Total</th></tr></thead><tbody>
{% for item in body.items %}<tr><td>{{ item.label }}</td><td class="num">{{ item.base|money }}</td>
<td class="num">{{ item.employee|money }}</td><td class="num">{{ item.employer|money }}</td><td class="num">{{ item.total|money }}</td></tr>{% endfor %}
<tr class="total"><td colspan="2">Total to pay</td><td class="num">{{ body.employee|money }}</td>
<td class="num">{{ body.employer|money }}</td><td class="num">{{ body.total|money }}</td></tr>
</tbody></table>
{% endfor %}
""",
    "Statement of contributions",
)

ANNUAL_STATEMENT = (
    "Annual individual salary statement",
    "PAYROLL",
    """
<h1>ANNUAL SALARY STATEMENT {{ year }}</h1>
"""
    + EMPLOYEE_BLOCK
    + """
<table class="no-border"><tr><td width="35%">CNPS n°</td><td>{{ employee.social_insurance_number|default:"—" }}</td></tr>
<tr><td>NIU</td><td>{{ employee.tax_identification_number|default:"—" }}</td></tr></table>
<table><thead><tr><th>Month</th><th class="num">Gross</th><th class="num">Taxable</th><th class="num">Contributory</th>
<th class="num">Emp. contrib.</th><th class="num">Taxes</th><th class="num">Net payable</th></tr></thead><tbody>
{% for p in payslips %}<tr><td>{{ p.period.month|stringformat:"02d" }}/{{ p.period.year }}</td><td class="num">{{ p.gross|money }}</td>
<td class="num">{{ p.taxable_base|money }}</td><td class="num">{{ p.contributory_base|money }}</td><td class="num">{{ p.employee_contributions|money }}</td>
<td class="num">{{ p.taxes|money }}</td><td class="num">{{ p.net_payable|money }}</td></tr>{% endfor %}
<tr class="total"><td>Total</td><td class="num">{{ totals.gross|money }}</td><td class="num">{{ totals.taxable_base|money }}</td>
<td class="num">{{ totals.contributory_base|money }}</td><td class="num">{{ totals.employee_contributions|money }}</td>
<td class="num">{{ totals.taxes|money }}</td><td class="num">{{ totals.net_payable|money }}</td></tr>
</tbody></table>
<h2>Detail of taxes and contributions withheld</h2>
<table>{% for item in withheld %}<tr><td>{{ item.label }}</td><td class="num">{{ item.amount|money }}</td></tr>{% endfor %}</table>
<p>Done on {{ today|date:"d/m/Y" }}.</p>
""",
    "Annual salary statement",
)

PAYMENT_ORDER = (
    "Payment order",
    "PAYROLL",
    """
<h1>PAYMENT ORDER – SALARIES {{ period.month|stringformat:"02d" }}/{{ period.year }}</h1>
<p>To: <b>{{ bank }}</b></p>
<p>Please debit our account of the total amount below and credit the accounts of the following
employees on {{ period.payment_date|date:"d/m/Y"|default:"the payment date" }}.</p>
<table><thead><tr><th>Matric.</th><th>Employee</th><th>Account</th><th class="num">Amount ({{ currency }})</th></tr></thead><tbody>
{% for p in payslips %}<tr><td>{{ p.employee.matriculation_number }}</td><td>{{ p.employee.full_name }}</td>
<td>{{ p.bank_account }}</td><td class="num">{{ p.net_payable|money }}</td></tr>{% endfor %}
<tr class="total"><td colspan="3">Total to debit ({{ count }} transfer(s))</td><td class="num">{{ total|money }}</td></tr>
</tbody></table>
<br/><table class="signature"><tr><td width="50%"><b>Prepared by</b></td><td><b>Authorised signatory</b><br/>{{ company.legal_representative }}</td></tr></table>
""",
    "Payment order",
)

CASH_LIST = (
    "Cash payment list",
    "PAYROLL",
    """
<h1>EMPLOYEES PAID IN CASH – {{ period.month|stringformat:"02d" }}/{{ period.year }}</h1>
<table><thead><tr><th>Matric.</th><th>Employee</th><th class="num">Net payable ({{ currency }})</th>
<th>Date</th><th width="30%">Signature (received)</th></tr></thead><tbody>
{% for p in payslips %}<tr><td>{{ p.employee.matriculation_number }}</td><td>{{ p.employee.full_name }}</td>
<td class="num">{{ p.net_payable|money }}</td><td></td><td style="height:28pt"></td></tr>{% endfor %}
<tr class="total"><td colspan="2">Total</td><td class="num">{{ total|money }}</td><td colspan="2"></td></tr>
</tbody></table>
""",
    "Cash payment list",
)

EMPLOYMENT_ATTESTATION = (
    "Employment attestation",
    "CERTIFICATE",
    """
<h1>EMPLOYMENT ATTESTATION</h1>
<p class="muted">Reference {{ reference }}</p>
<p>I, the undersigned, {{ company.legal_representative }}, acting for {{ company.corporate_name }}, certify that</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>has been employed by our organisation since <b>{{ employee.date_of_hire|date:"d/m/Y" }}</b>
and currently holds the position of <b>{{ employee.position.title|default:"" }}</b>
under a {{ employee.get_contract_type_display|lower }}.</p>
<p>This attestation is issued at the request of the person concerned to serve and be used as required.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p><br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
""",
    "Employment attestation",
)

SALARY_ATTESTATION = (
    "Salary attestation",
    "CERTIFICATE",
    """
<h1>SALARY ATTESTATION</h1>
<p class="muted">Reference {{ reference }}</p>
<p>We certify that</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>employed since {{ employee.date_of_hire|date:"d/m/Y" }} as {{ employee.position.title|default:"" }},
receives a monthly base salary of <b>{{ base_salary|money }} {{ currency }}</b>
{% if average_net %}and received an average monthly net salary of <b>{{ average_net|money }} {{ currency }}</b>
over the last {{ months }} month(s){% endif %}.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p><br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
""",
    "Salary attestation",
)

PRESENCE_ATTESTATION = (
    "Attestation of presence",
    "CERTIFICATE",
    """
<h1>ATTESTATION OF PRESENCE</h1>
<p class="muted">Reference {{ reference }}</p>
<p>We certify that</p>
"""
    + EMPLOYEE_BLOCK
    + """
<p>is a member of our staff and is present at work{% if site %} at {{ site }}{% endif %}
on the date of this attestation.</p>
{% if days_present %}<p>Days of presence recorded from {{ start|date:"d/m/Y" }} to {{ end|date:"d/m/Y" }}:
<b>{{ days_present }}</b>.</p>{% endif %}
<p>Done on {{ today|date:"d/m/Y" }}.</p><br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
""",
    "Attestation of presence",
)

DECISION_BODY = (
    """
<p class="muted">Reference {{ reference }}</p>
<p>The management of {{ company.corporate_name }},</p>
<p>Considering the Labour Code, the collective agreement and the internal rules,</p>
<p>Considering the personal record of</p>
"""
    + EMPLOYEE_BLOCK
    + """
<h2>Decides</h2>
<p><b>Article 1.</b> {{ subject }}</p>
{% if details %}<p><b>Article 2.</b> {{ details|linebreaksbr }}</p>{% endif %}
<p><b>Article {% if details %}3{% else %}2{% endif %}.</b> This decision takes effect on
<b>{{ effective_date|date:"d/m/Y" }}</b>.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p><br/><p><b>{{ company.legal_representative }}</b>{% if company.legal_representative_title %}<br/>{{ company.legal_representative_title }}{% endif %}</p>
"""
)

PROMOTION_DECISION = (
    "Promotion decision",
    "DECISION",
    "<h1>PROMOTION DECISION</h1>" + DECISION_BODY,
    "Promotion decision",
)
TRANSFER_DECISION = (
    "Transfer decision",
    "DECISION",
    "<h1>TRANSFER DECISION</h1>" + DECISION_BODY,
    "Transfer decision",
)
SALARY_REVISION_DECISION = (
    "Salary revision decision",
    "DECISION",
    "<h1>SALARY REVISION DECISION</h1>" + DECISION_BODY,
    "Salary revision",
)
ASSIGNMENT_DECISION = (
    "Temporary assignment decision",
    "DECISION",
    "<h1>ASSIGNMENT DECISION</h1>" + DECISION_BODY,
    "Assignment decision",
)
DISCIPLINARY_LETTER = (
    "Disciplinary letter",
    "DECISION",
    """
<h1>DISCIPLINARY LETTER</h1>
<p class="muted">Reference {{ reference }}</p>
<p>To {{ employee.given_names }} {{ employee.surname }} ({{ employee.matriculation_number }})</p>
<p><b>Subject: {{ subject }}</b></p>
<p>{{ details|linebreaksbr }}</p>
<p>This measure takes effect on {{ effective_date|date:"d/m/Y" }} and is recorded in your personal file.</p>
<p>Done on {{ today|date:"d/m/Y" }}.</p>
""" + SIGNATURES,
    "Disciplinary letter",
)

DEFAULT_TEMPLATES = {
    "PAYSLIP": PAYSLIP,
    "PAYROLL_BOOK": PAYROLL_BOOK,
    "CONTRIBUTION_STATEMENT": CONTRIBUTION_STATEMENT,
    "ANNUAL_STATEMENT": ANNUAL_STATEMENT,
    "PAYMENT_ORDER": PAYMENT_ORDER,
    "CASH_LIST": CASH_LIST,
    "EMPLOYMENT_ATTESTATION": EMPLOYMENT_ATTESTATION,
    "SALARY_ATTESTATION": SALARY_ATTESTATION,
    "PRESENCE_ATTESTATION": PRESENCE_ATTESTATION,
    "PROMOTION_DECISION": PROMOTION_DECISION,
    "TRANSFER_DECISION": TRANSFER_DECISION,
    "DISCIPLINARY_LETTER": DISCIPLINARY_LETTER,
    "SALARY_REVISION_DECISION": SALARY_REVISION_DECISION,
    "ASSIGNMENT_DECISION": ASSIGNMENT_DECISION,
    "CONTRACT": CONTRACT,
    "AMENDMENT": AMENDMENT,
    "WORK_CERTIFICATE": WORK_CERTIFICATE,
    "END_OF_CONTRACT": END_OF_CONTRACT,
    "LEAVE_DECISION": LEAVE_DECISION,
    "LEAVE_CERTIFICATE": LEAVE_CERTIFICATE,
    "LEAVE_BALANCE": LEAVE_BALANCE,
}


def refresh_untouched_templates(DocumentTemplate=None):
    """Update the default templates that were never modified by a user."""
    if DocumentTemplate is None:
        from .models import DocumentTemplate
    for code, (name, category, body, footer) in DEFAULT_TEMPLATES.items():
        DocumentTemplate.objects.filter(code=code, updated_by__isnull=True).update(
            body=body, footer=footer
        )
    sync_default_templates(DocumentTemplate)


def sync_default_templates(DocumentTemplate=None):
    """Create the default templates that do not exist yet."""
    if DocumentTemplate is None:
        from .models import DocumentTemplate
    for code, (name, category, body, footer) in DEFAULT_TEMPLATES.items():
        DocumentTemplate.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "category": category,
                "body": body,
                "footer": footer,
            },
        )
