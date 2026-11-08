"""
M-12: production of the printable documents from the configurable templates.
"""

from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify

from core.models import Sequence
from core.pdf import html_to_pdf, render_template_string, wrap_document

from .models import DocumentTemplate, IssuedDocument

DUPLICATE_BANNER = '<p class="duplicate">DUPLICATE</p>'


class TemplateMissing(Exception):
    pass


def get_template(code):
    template = DocumentTemplate.objects.filter(code=code, is_active=True).first()
    if template is None:
        from .default_templates import DEFAULT_TEMPLATES

        if code not in DEFAULT_TEMPLATES:
            raise TemplateMissing(f"No document template '{code}'.")
        name, category, body, footer = DEFAULT_TEMPLATES[code]
        template = DocumentTemplate.objects.create(
            code=code, name=name, category=category, body=body, footer=footer
        )
    return template


def template_body_html(template, duplicate=False):
    body = template.body
    if template.signature_block:
        body += template.signature_block
    if duplicate:
        body = DUPLICATE_BANNER + body
    return body


def render_html(code, context, duplicate=False, landscape=False):
    template = get_template(code)
    body = template_body_html(template, duplicate)
    context = {"today": timezone.now().date(), **context}
    return render_template_string(
        wrap_document(body, template.footer or template.name, landscape), context
    )


def render_document(code, context, duplicate=False, landscape=False):
    """Return the PDF bytes of a single document."""
    return html_to_pdf(render_html(code, context, duplicate, landscape))


def render_batch(code, contexts, duplicate=False):
    """BN-114: several documents in one single PDF file (one per page)."""
    template = get_template(code)
    body = template_body_html(template, duplicate)
    pages = []
    for index, context in enumerate(contexts):
        context = {"today": timezone.now().date(), **context}
        page = render_template_string(body, context)
        prefix = "" if index == 0 else "<pdf:nextpage/>"
        pages.append(prefix + _header_html(context) + page)
    html = wrap_document(
        "", template.footer or template.name, include_header=False
    ).replace("</body>", "".join(pages) + "</body>", 1)
    return html_to_pdf(html)


def _header_html(context):
    from core.pdf import HEADER_HTML

    return render_template_string(HEADER_HTML, context)


def next_reference(code):
    year = timezone.now().year
    number = Sequence.next_value(f"document-{code}-{year}")
    return f"{code}-{year}-{number:05d}"


def issue_document(
    code,
    context,
    employee=None,
    user=None,
    recipient="",
    title=None,
    duplicate=False,
    pdf=None,
    reference=None,
):
    """
    Produce a document and keep a copy of it (BN-127).
    `pdf` can be given when the bytes were already produced (batch files).
    """
    template = get_template(code)
    reference = reference or next_reference(code)
    context = {**context, "reference": reference}
    if pdf is None:
        pdf = render_document(code, context, duplicate=duplicate)
    title = title or template.name
    if employee is not None:
        title = f"{title} - {employee.full_name}"
        recipient = recipient or employee.full_name
    issued = IssuedDocument(
        template_code=code,
        title=title,
        reference=reference,
        employee=employee,
        recipient=recipient,
        is_duplicate=duplicate,
        issued_by=user,
    )
    issued.file.save(
        f"{slugify(title)[:80]}-{reference}.pdf", ContentFile(pdf), save=True
    )
    return issued
