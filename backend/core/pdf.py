"""
PDF production for every printable document of the system (M-12).

Documents are HTML rendered with the Django template engine, then converted
with xhtml2pdf. The organisation header (logo, legal identification) is added
to every document so that it is identical everywhere (BN-01).
"""

import io

from django.template import Context, Template
from django.utils.html import escape

BASE_CSS = """
@page { size: a4 portrait; margin: 1.5cm 1.5cm 2cm 1.5cm;
        @frame footer { -pdf-frame-content: page-footer; bottom: 0.8cm;
                        margin-left: 1.5cm; margin-right: 1.5cm; height: 1cm; } }
@page landscape { size: a4 landscape; margin: 1.2cm; }
body { font-family: Helvetica; font-size: 9pt; color: #222; }
h1 { font-size: 15pt; margin: 0 0 6pt 0; color: #1d2b6b; }
h2 { font-size: 11pt; margin: 10pt 0 4pt 0; color: #1d2b6b; }
table { width: 100%; border-collapse: collapse; }
th { background-color: #e8ecf7; font-weight: bold; text-align: left; }
th, td { border: 0.5pt solid #9aa3b5; padding: 2pt 3pt; vertical-align: top; }
td.num, th.num { text-align: right; }
.no-border td, .no-border th { border: none; }
.muted { color: #666; }
.header td { border: none; padding: 0; }
.total td { font-weight: bold; background-color: #f2f4fa; }
.duplicate { color: #b00020; font-size: 14pt; font-weight: bold; text-align: center; }
.signature td { border: none; height: 60pt; vertical-align: top; }
"""


def company_context():
    from organisation.models import CompanyIdentity

    company = CompanyIdentity.objects.first()
    logo_path = None
    if company and company.logo:
        try:
            logo_path = company.logo.path
        except (ValueError, NotImplementedError):
            logo_path = None
    return {"company": company, "company_logo_path": logo_path}


HEADER_HTML = """
<table class="header"><tr>
  <td width="20%">{% if company_logo_path %}<img src="{{ company_logo_path }}" height="50"/>{% endif %}</td>
  <td width="80%">
    <b style="font-size:12pt">{{ company.corporate_name|default:"" }}</b>
    {% if company.legal_form %} — {{ company.legal_form }}{% endif %}<br/>
    {{ company.address|default:"" }}<br/>
    {% if company.registration_number %}RCCM: {{ company.registration_number }} · {% endif %}
    {% if company.tax_id %}NIU: {{ company.tax_id }} · {% endif %}
    {% if company.social_insurance_number %}CNPS: {{ company.social_insurance_number }}{% endif %}
  </td>
</tr></table><hr/>
"""


def wrap_document(body_html, footer_text="", landscape=False, include_header=True):
    page = '<pdf:nexttemplate name="landscape"/>' if landscape else ""
    header = HEADER_HTML if include_header else ""
    # The footer frame content is declared first: placed at the end of the
    # body it would take space in the flow and push a full page onto a new one.
    return (
        f"<html><head><meta charset='utf-8'/><style>{BASE_CSS}</style></head><body>"
        f"<div id='page-footer' class='muted'>{footer_text} — page <pdf:pagenumber/>"
        f" / <pdf:pagecount/></div>{page}{header}{body_html}</body></html>"
    )


def render_template_string(template_html, context):
    full_context = {**company_context(), **context}
    return Template(template_html).render(Context(full_context))


def html_to_pdf(html):
    from xhtml2pdf import pisa

    buffer = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding="utf-8")
    if result.err:
        raise ValueError("The PDF document could not be generated.")
    return buffer.getvalue()


def render_pdf(body_template, context, footer_text="", landscape=False):
    """Render a body template (Django syntax) into a complete PDF document."""
    html = render_template_string(
        wrap_document(body_template, footer_text, landscape), context
    )
    return html_to_pdf(html)


def render_table_pdf(title, headers, rows):
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
        for row in rows
    )
    landscape = len(headers) > 7
    body_html = (
        f"<h1>{escape(title)}</h1><table><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )
    return render_pdf(body_html, {}, footer_text=escape(title), landscape=landscape)
