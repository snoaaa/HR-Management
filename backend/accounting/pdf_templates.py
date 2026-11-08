"""Layout of the accounting documents (rendered by core.pdf)."""

BOOK_TEMPLATE = """
<h1>{{ title }}</h1>
<p class="doc-meta">{{ subtitle }}</p>
{% if kind == "journal" %}
{% for e in rows %}<h2>{{ e.journal.code }} · {{ e.number }} · {{ e.date|date:"d/m/Y" }} · {{ e.label }}</h2>
<table repeat="1"><thead><tr><th width="14%">Account</th><th width="32%">Account name</th><th>Label</th>
<th class="num" width="14%">Debit</th><th class="num" width="14%">Credit</th></tr></thead>
{% for l in e.lines.all %}<tr class="{% cycle '' 'alt' %}"><td>{{ l.account.number }}</td><td>{{ l.account.name }}</td>
<td>{{ l.label }}</td><td class="num">{{ l.debit|nonzero_money }}</td><td class="num">{{ l.credit|nonzero_money }}</td></tr>{% endfor %}
<tr class="total"><td colspan="3">Total of the entry</td><td class="num">{{ e.total_debit|money }}</td>
<td class="num">{{ e.total_credit|money }}</td></tr></table>{% empty %}<p class="muted">No entry in the period.</p>{% endfor %}
{% if rows %}<table><tr class="total"><td>Total of the journal book ({{ rows|length }} entries)</td>
<td class="num" width="14%">{{ totals.debit|money }}</td><td class="num" width="14%">{{ totals.credit|money }}</td></tr></table>{% endif %}
{% elif kind == "ledger" %}
{% for a in rows %}<h2>{{ a.account }} · {{ a.name }}</h2>
<table repeat="1"><thead><tr><th width="10%">Date</th><th width="12%">Entry</th><th>Label</th><th class="num" width="13%">Debit</th>
<th class="num" width="13%">Credit</th><th class="num" width="14%">Balance</th></tr></thead>
<tr><td colspan="5" class="muted">Opening balance</td><td class="num">{{ a.opening|money }}</td></tr>
{% for l in a.lines %}<tr class="{% cycle '' 'alt' %}"><td>{{ l.date|date:"d/m/Y" }}</td><td>{{ l.entry }}</td><td>{{ l.label }}</td>
<td class="num">{{ l.debit|nonzero_money }}</td><td class="num">{{ l.credit|nonzero_money }}</td>
<td class="num">{{ l.balance|money }}</td></tr>{% endfor %}
<tr class="total"><td colspan="3">Totals and closing balance</td><td class="num">{{ a.debit|money }}</td>
<td class="num">{{ a.credit|money }}</td><td class="num">{{ a.closing|money }}</td></tr></table>
{% empty %}<p class="muted">No movement in the period.</p>{% endfor %}
{% elif kind == "voucher" %}
<table class="no-border" style="margin-bottom:8pt"><tr>
<th width="18%">Journal</th><td width="32%">{{ entry.journal.code }} · {{ entry.journal.name }}</td>
<th width="18%">Entry number</th><td>{{ entry.number }}</td></tr>
<tr><th>Date</th><td>{{ entry.date|date:"d/m/Y" }}</td><th>Reference</th><td>{{ entry.reference|default:"—" }}</td></tr>
<tr><th>Label</th><td colspan="3">{{ entry.label }}</td></tr>
{% if entry.payroll_period %}<tr><th>Payroll period</th><td colspan="3">{{ entry.payroll_period }}</td></tr>{% endif %}
</table>
<table repeat="1"><thead><tr><th width="11%">Account</th><th width="25%">Account name</th><th>Label</th><th width="16%">Analytic</th>
<th class="num" width="12%">Debit</th><th class="num" width="12%">Credit</th></tr></thead>
{% for l in entry.lines.all %}<tr class="{% cycle '' 'alt' %}"><td>{{ l.account.number }}</td><td>{{ l.account.name }}</td>
<td>{{ l.label }}{% if l.employee %}<br/><span class="small muted">{{ l.employee.full_name }}</span>{% endif %}</td>
<td class="small">{{ l.department.name|default:"" }}{% if l.cost_centre %} · {{ l.cost_centre.name }}{% endif %}</td>
<td class="num">{{ l.debit|nonzero_money }}</td><td class="num">{{ l.credit|nonzero_money }}</td></tr>{% endfor %}
<tr class="total"><td colspan="4">Totals</td><td class="num">{{ entry.total_debit|money }}</td>
<td class="num">{{ entry.total_credit|money }}</td></tr></table>
<table class="signature" style="margin-top:18pt"><tr><td width="33%"><b>Prepared by</b><br/>
<span class="small muted">{{ entry.created_by|default:"" }}</span></td>
<td width="33%"><b>Checked by</b></td><td><b>Approved by</b></td></tr></table>
{% elif kind == "reconciliation" %}
<p class="highlight">{% if data.ok %}The payroll and the accounting agree for this period.{% elif not data.posted %}No payroll
entry has been posted for this period yet.{% else %}Differences exist between the payroll and the accounting: check them below.{% endif %}</p>
<table><thead><tr><th>Control</th><th class="num">Payroll</th><th class="num">Accounting</th><th class="num">Difference</th></tr></thead>
{% for c in data.checks %}<tr class="{% cycle '' 'alt' %}"><td>{{ c.label }}</td><td class="num">{{ c.payroll|money }}</td>
<td class="num">{{ c.accounting|money }}</td><td class="num">{{ c.difference|money }}</td></tr>{% endfor %}</table>
{% elif kind == "statements" %}
<h2>Statement of income (personnel items)</h2>
<table><thead><tr><th>Item</th><th width="18%">Accounts</th><th class="num" width="20%">Amount</th></tr></thead>
<tr><td>Personnel expenses</td><td>66</td><td class="num">{{ data.personnel_expenses_66|money }}</td></tr>
<tr class="alt"><td>Taxes on salaries</td><td>6413</td><td class="num">{{ data.taxes_on_salaries_6413|money }}</td></tr></table>
<h2>Balance sheet (liabilities at 31/12/{{ data.year }})</h2>
<table><thead><tr><th>Item</th><th width="18%">Accounts</th><th class="num" width="20%">Amount</th></tr></thead>
<tr><td>Personnel</td><td>42</td><td class="num">{{ data.liabilities_to_personnel_42|money }}</td></tr>
<tr class="alt"><td>Social bodies</td><td>43</td><td class="num">{{ data.liabilities_to_social_bodies_43|money }}</td></tr>
<tr><td>State and local authorities</td><td>44</td><td class="num">{{ data.liabilities_to_state_44|money }}</td></tr></table>
<h2>Notes</h2>
<table class="no-border"><tr><th width="40%">Average headcount</th><td>{{ data.average_headcount }}</td></tr>
<tr><th>Months with a payroll</th><td>{{ data.months_with_payroll }}</td></tr></table>
{% else %}
<table repeat="1"><thead><tr>{% for h in columns %}<th width="{{ h.width }}%" class="{% if forloop.counter > numeric_from %}num{% endif %}">{{ h.label }}</th>{% endfor %}</tr></thead>
{% for r in table %}<tr class="{% cycle '' 'alt' %}">{% for v in r %}<td class="{% if forloop.counter > numeric_from %}num{% endif %}">
{% if forloop.counter > numeric_from %}{{ v|money }}{% else %}{{ v|default_if_none:"" }}{% endif %}</td>{% endfor %}</tr>
{% empty %}<tr><td colspan="{{ columns|length }}" class="muted">Nothing to report.</td></tr>{% endfor %}
{% if totals_row %}<tr class="total">{% for v in totals_row %}<td class="{% if forloop.counter > numeric_from %}num{% endif %}">
{% if forloop.counter > numeric_from and v != "" %}{{ v|money }}{% else %}{{ v }}{% endif %}</td>{% endfor %}</tr>{% endif %}
</table>{% endif %}
"""
