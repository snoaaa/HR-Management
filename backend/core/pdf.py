"""
PDF production for every printable document of the system (M-12).

Documents are HTML rendered with the Django template engine, then converted
with xhtml2pdf. Every document shares the same professional layout in the
colours of the application (Odoo purple #714B67 and teal #00A09D, flat
colours only): the organisation header with its logo and legal
identification (BN-01), a coloured title, styled tables and a footer with
the page numbers.
"""

import io
from decimal import Decimal, InvalidOperation

from django.template import Context, Template
from django.utils import timezone
from django.utils.html import escape

PURPLE = "#714B67"
PURPLE_DARK = "#4a2f42"
PURPLE_LIGHT = "#f5f0f3"
TEAL = "#00A09D"
TEXT = "#2d1f29"
MUTED = "#6b5565"
BORDER = "#e8dde5"

_FOOTER_FRAME = (
    "@frame footer { -pdf-frame-content: page-footer; bottom: 0.7cm; "
    "margin-left: 1.6cm; margin-right: 1.6cm; height: 0.9cm; }"
)

BASE_CSS = f"""
@page {{ size: a4 portrait; margin: 1.4cm 1.6cm 2.0cm 1.6cm; {_FOOTER_FRAME} }}
@page landscape {{ size: a4 landscape; margin: 1.2cm 1.4cm 1.8cm 1.4cm; {_FOOTER_FRAME} }}
body {{ font-family: Helvetica; font-size: 8.8pt; color: {TEXT}; line-height: 1.35; }}
h1 {{ font-size: 15pt; margin: 4pt 0 2pt 0; color: {PURPLE}; text-transform: uppercase;
     border-left: 4pt solid {TEAL}; padding: 2pt 0 2pt 7pt; }}
h2 {{ font-size: 10.5pt; margin: 10pt 0 4pt 0; color: {PURPLE_DARK}; padding-bottom: 2pt;
     border-bottom: 0.8pt solid {BORDER}; }}
p {{ margin: 3pt 0; }}
table {{ width: 100%; }}
th {{ background-color: {PURPLE}; color: #ffffff; font-weight: bold; font-size: 8pt; text-align: left;
     padding: 4pt 4pt 3pt 4pt; border: 0.5pt solid {PURPLE}; }}
td {{ padding: 3pt 4pt 2pt 4pt; border-bottom: 0.5pt solid {BORDER}; vertical-align: top; }}
tr.alt td {{ background-color: #faf8f9; }}
td.num, th.num {{ text-align: right; }}
.no-border td, .no-border th {{ border: none; background-color: transparent; color: {TEXT}; padding: 1pt 4pt; }}
.no-border th {{ font-weight: bold; }}
.muted {{ color: {MUTED}; }}
.small {{ font-size: 7.5pt; }}
.header td {{ border: none; padding: 0; vertical-align: middle; }}
.company-name {{ font-size: 13pt; font-weight: bold; color: {PURPLE}; }}
.company-legal {{ font-size: 7.5pt; color: {MUTED}; }}
.rule {{ border-bottom: 2pt solid {PURPLE}; margin: 6pt 0 1pt 0; }}
.rule-teal {{ border-bottom: 0.8pt solid {TEAL}; margin: 0 0 8pt 0; }}
.doc-meta {{ font-size: 7.5pt; color: {MUTED}; margin: 0 0 8pt 0; }}
.total td {{ font-weight: bold; background-color: {PURPLE_LIGHT}; border-top: 1pt solid {PURPLE}; }}
.highlight {{ background-color: {PURPLE_LIGHT}; padding: 6pt; border-left: 3pt solid {TEAL}; }}
.badge {{ color: #ffffff; background-color: {TEAL}; padding: 1pt 4pt; font-size: 7.5pt; }}
.duplicate {{ color: #b00020; font-size: 13pt; font-weight: bold; text-align: center;
             border: 1pt solid #b00020; padding: 3pt; }}
.signature td {{ border: none; height: 60pt; vertical-align: top; }}
/* Styling the footer frame itself hides the page numbers: style its table. */
table.footer td {{ font-size: 7pt; color: {MUTED}; border: none; border-top: 0.8pt solid {PURPLE};
                  padding: 3pt 0 0 0; background-color: transparent; }}
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
  <td width="22%">{% if company_logo_path %}<img src="{{ company_logo_path }}" height="54"/>{% endif %}</td>
  <td width="78%" style="text-align:right">
    <span class="company-name">{{ company.corporate_name|default:"" }}</span>{% if company.legal_form %}
    <span class="company-legal"> · {{ company.legal_form }}</span>{% endif %}<br/>
    <span class="company-legal">{{ company.address|default:"" }}
    {% if company.postal_box %} · P.O. Box {{ company.postal_box }}{% endif %}
    {% if company.city %} · {{ company.city }}{% endif %}</span><br/>
    {% if company.phone or company.email or company.website %}<span class="company-legal">
    {% if company.phone %}Tel. {{ company.phone }}{% endif %}
    {% if company.email %} · {{ company.email }}{% endif %}
    {% if company.website %} · {{ company.website }}{% endif %}
    </span><br/>{% endif %}
    <span class="company-legal">
    {% if company.registration_number %}RCCM {{ company.registration_number }}{% endif %}
    {% if company.tax_id %} · NIU {{ company.tax_id }}{% endif %}
    {% if company.social_insurance_number %} · CNPS {{ company.social_insurance_number }}{% endif %}
    </span>
  </td>
</tr></table>
<div class="rule"></div><div class="rule-teal"></div>
"""


def _footer(footer_text):
    stamp = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    return (
        "<div id='page-footer'><table class='footer'><tr>"
        "<td width='75%'>{% if company %}{{ company.corporate_name }} · {% endif %}"
        f"{footer_text} · generated on {stamp}</td>"
        "<td width='25%' style='text-align:right'>page <pdf:pagenumber/> / <pdf:pagecount/></td>"
        "</tr></table></div>"
    )


def wrap_document(body_html, footer_text="", landscape=False, include_header=True):
    page = '<pdf:nexttemplate name="landscape"/><pdf:nextpage/>' if landscape else ""
    header = HEADER_HTML if include_header else ""
    # The footer frame content is declared first: placed at the end of the
    # body it would take space in the flow and push a full page onto a new one.
    return (
        f"<html><head><meta charset='utf-8'/><style>{BASE_CSS}</style></head><body>"
        f"{_footer(footer_text)}{page}{header}{body_html}</body></html>"
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
    pdf = buffer.getvalue()
    return _drop_blank_first_page(pdf)


def _drop_blank_first_page(pdf):
    """The landscape template switch leaves an empty first portrait page."""
    if b"/Count 1" in pdf[:2000]:
        return pdf
    try:
        from pypdf import PdfReader, PdfWriter

        reader = PdfReader(io.BytesIO(pdf))
        if len(reader.pages) > 1 and not (
            reader.pages[0].extract_text() or ""
        ).strip().replace("page", ""):
            writer = PdfWriter()
            for page in reader.pages[1:]:
                writer.add_page(page)
            out = io.BytesIO()
            writer.write(out)
            return out.getvalue()
    except Exception:
        pass
    return pdf


def render_pdf(body_template, context, footer_text="", landscape=False):
    """Render a body template (Django syntax) into a complete PDF document."""
    html = render_template_string(
        wrap_document(body_template, footer_text, landscape), context
    )
    return html_to_pdf(html)


def _is_number(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float, Decimal)):
        return True
    try:
        Decimal(str(value).replace(" ", "").replace(" ", ""))
        return str(value).strip() != ""
    except (InvalidOperation, ValueError):
        return False


def _format_cell(value):
    from core.templatetags.hrms import money

    if value is None:
        return ""
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        number = Decimal(str(value))
        return money(number, 0 if number == number.to_integral_value() else 2)
    return str(value)


def numeric_columns(headers, rows):
    return [
        bool(rows)
        and all(
            _is_number(row[i]) or row[i] in ("", None) for row in rows if i < len(row)
        )
        and any(_is_number(row[i]) for row in rows if i < len(row))
        for i in range(len(headers))
    ]


def column_widths(headers, rows, numeric=None):
    """Widths in % following the content: amounts narrow, labels wide."""
    if numeric is None:
        numeric = numeric_columns(headers, rows)
    weights = []
    for i, header in enumerate(headers):
        cells = [len(_format_cell(row[i])) for row in rows[:200] if i < len(row)]
        longest = max(cells or [0])
        if numeric[i]:
            weight = min(max(longest + 1, len(header) * 0.8, 8), 15)
        else:
            weight = min(max(longest, len(header), 5), 42)
        weights.append(weight)
    total = sum(weights) or 1
    return [round(w * 100 / total, 1) for w in weights]


def render_table_pdf(title, headers, rows, subtitle=""):
    """A list of the application as a themed PDF (BN-126)."""
    numeric = numeric_columns(headers, rows)
    widths = column_widths(headers, rows, numeric)
    head = "".join(
        f"<th width='{widths[i]}%' class='{'num' if numeric[i] else ''}'>"
        f"{escape(h)}</th>"
        for i, h in enumerate(headers)
    )
    body = "".join(
        f"<tr class='{'alt' if index % 2 else ''}'>"
        + "".join(
            f"<td class='{'num' if numeric[i] else ''}'>{escape(_format_cell(v))}</td>"
            for i, v in enumerate(row)
        )
        + "</tr>"
        for index, row in enumerate(rows)
    )
    landscape = len(headers) > 7
    stamp = timezone.localtime().strftime("%d/%m/%Y")
    meta = f"{escape(subtitle)} · " if subtitle else ""
    body_html = (
        f"<h1>{escape(title)}</h1>"
        f"<p class='doc-meta'>{meta}{len(rows)} line(s) · situation on {stamp}</p>"
        f"<table repeat='1'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )
    return render_pdf(body_html, {}, footer_text=escape(title), landscape=landscape)
