"""Layout of the employee record sheet (rendered by core.pdf)."""

RECORD_TEMPLATE = """
<table class="no-border"><tr>
{% if photo_path %}<td width="16%"><img src="{{ photo_path }}" width="70" height="80"/></td>{% endif %}
<td><h1>Employee record</h1>
<p><span class="company-name">{{ e.get_title_display }} {{ e.surname|upper }} {{ e.given_names }}</span><br/>
<span class="muted">Matriculation {{ e.matriculation_number }} · {{ e.position.title|default:"No position" }} · {{ e.department.name|default:"No department" }}</span><br/>
<span class="badge">{{ e.get_status_display }}</span></p></td></tr></table>

<h2>Civil identity</h2>
<table class="no-border">
<tr><th width="25%">Surname</th><td width="25%">{{ e.surname }}</td><th width="25%">Given names</th><td>{{ e.given_names }}</td></tr>
<tr><th>Maiden name</th><td>{{ e.maiden_name|default:"—" }}</td><th>Sex</th><td>{{ e.get_sex_display }}</td></tr>
<tr><th>Date of birth</th><td>{{ e.date_of_birth|date:"d/m/Y" }} ({{ e.age }} years)</td><th>Place of birth</th><td>{{ e.place_of_birth }}</td></tr>
<tr><th>Nationality</th><td>{{ e.nationality }}</td><th>Marital status</th><td>{{ e.get_marital_status_display }}</td></tr>
<tr><th>Identity document</th><td>{{ e.identity_document_type }} n° {{ e.identity_document_number }}</td>
<th>Issued</th><td>{{ e.identity_document_issue_date|date:"d/m/Y"|default:"—" }}{% if e.identity_document_issue_place %} at {{ e.identity_document_issue_place }}{% endif %}</td></tr>
<tr><th>Valid until</th><td>{{ e.identity_document_validity|date:"d/m/Y"|default:"—" }}</td><th>Blood group</th><td>{{ e.blood_group|default:"—" }}</td></tr>
<tr><th>Education level</th><td>{{ e.get_education_level_display|default:"—" }}</td><th>Languages</th><td>{{ e.spoken_languages|default:"—" }}</td></tr>
</table>

<h2>Contact details</h2>
<table class="no-border">
<tr><th width="25%">Address</th><td colspan="3">{{ e.address }}</td></tr>
<tr><th>City / Region</th><td width="25%">{{ e.city|default:"—" }}{% if e.region %} · {{ e.get_region_display }}{% endif %}</td>
<th width="25%">P.O. Box</th><td>{{ e.postal_box|default:"—" }}</td></tr>
<tr><th>Telephone</th><td>{{ e.phone_number }}{% if e.phone_number_2 %} · {{ e.phone_number_2 }}{% endif %}</td>
<th>Professional telephone</th><td>{{ e.professional_phone|default:"—" }}</td></tr>
<tr><th>Personal e-mail</th><td>{{ e.personal_email|default:"—" }}</td><th>Professional e-mail</th><td>{{ e.professional_email|default:"—" }}</td></tr>
<tr><th>Emergency contact</th><td colspan="3">{{ e.emergency_contact_name }} ({{ e.emergency_contact_relationship }}) · {{ e.emergency_contact_number }}
{% if e.emergency_contact_name_2 %}<br/>{{ e.emergency_contact_name_2 }} ({{ e.emergency_contact_relationship_2 }}) · {{ e.emergency_contact_number_2 }}{% endif %}</td></tr>
</table>

<h2>Administrative situation</h2>
<table class="no-border">
<tr><th width="25%">Date of hire</th><td width="25%">{{ e.date_of_hire|date:"d/m/Y" }}</td><th width="25%">Seniority</th><td>{{ e.seniority_years|floatformat:1 }} years</td></tr>
<tr><th>Contract type</th><td>{{ e.get_contract_type_display }}</td><th>Classification</th><td>{{ e.classification|default:"—" }}</td></tr>
<tr><th>Workplace</th><td>{{ e.workplace.name|default:"—" }}</td><th>Payment method</th><td>{{ e.get_method_of_payment_display }}</td></tr>
<tr><th>CNPS number</th><td>{{ e.social_insurance_number|default:"—" }}</td><th>CNPS registration</th><td>{{ e.cnps_registration_date|date:"d/m/Y"|default:"—" }}</td></tr>
<tr><th>Taxpayer number (NIU)</th><td>{{ e.tax_identification_number|default:"—" }}</td><th>Professional card</th><td>{{ e.professional_identification|default:"—" }}</td></tr>
<tr><th>Bank</th><td colspan="3">{{ e.bank_name|default:"—" }}{% if e.bank_branch %} · {{ e.bank_branch }}{% endif %}{% if e.account_number %} · account {{ e.account_number }} {{ e.bank_key|default:"" }}{% endif %}</td></tr>
{% if contract %}<tr><th>Current contract</th><td colspan="3">{{ contract.get_contract_type_display }} {{ contract.reference }} since {{ contract.start_date|date:"d/m/Y" }}{% if contract.end_date %} until {{ contract.end_date|date:"d/m/Y" }}{% endif %}</td></tr>{% endif %}
</table>

<h2>Family ({{ family|length }})</h2>
{% if family %}<table><thead><tr><th>Name</th><th width="20%">Relationship</th><th width="20%">Date of birth</th></tr></thead>
{% for f in family %}<tr class="{% cycle '' 'alt' %}"><td>{{ f.name }}</td><td>{{ f.get_relationship_display }}</td><td>{{ f.date_of_birth|date:"d/m/Y" }}</td></tr>{% endfor %}</table>
{% else %}<p class="muted">No family member recorded.</p>{% endif %}

<h2>Education and experience</h2>
{% if education %}<table><thead><tr><th width="20%">Type</th><th>Title</th><th width="30%">Institution / company</th><th width="17%">Period</th></tr></thead>
{% for x in education %}<tr class="{% cycle '' 'alt' %}"><td>{{ x.get_entry_type_display }}</td><td>{{ x.title }}</td><td>{{ x.institution_or_company }}</td>
<td>{{ x.start_date|date:"m/Y" }}{% if x.end_date %} – {{ x.end_date|date:"m/Y" }}{% endif %}</td></tr>{% endfor %}</table>
{% else %}<p class="muted">Nothing recorded.</p>{% endif %}
"""
