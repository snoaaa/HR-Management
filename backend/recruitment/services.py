"""Business rules of M-03."""

import datetime

from django.db import transaction
from django.utils import timezone

from employees.models import Employee, EmployeeDocument, EmployeeHistory
from notifications.services import notify, start_approval, users_with_roles
from users.models import User

from .models import ApplicationEvent, OnboardingTask

# BN-26: default onboarding items: (title, responsible role, days after hiring).
ONBOARDING_CHECKLIST = (
    ("Employment contract signed", User.Roles.HR_OFFICER, 0),
    ("Declaration to the social insurance (CNPS)", User.Roles.PAYROLL_OFFICER, 8),
    ("Bank details collected", User.Roles.PAYROLL_OFFICER, 5),
    ("Workstation ready", User.Roles.HEAD_OF_DEPARTMENT, 0),
    ("Badge issued", User.Roles.HR_OFFICER, 1),
    ("IT accounts created", User.Roles.SYSTEM_ADMINISTRATOR, 0),
    ("Equipment handed over", User.Roles.HEAD_OF_DEPARTMENT, 1),
    (
        "Welcome meeting and presentation of the internal rules",
        User.Roles.HR_MANAGER,
        2,
    ),
)
NEXT_STAGES = {
    "RECEIVED": {"PRESELECTED", "REJECTED"},
    "PRESELECTED": {"INTERVIEW", "TEST", "REJECTED"},
    "INTERVIEW": {"TEST", "SELECTED", "REJECTED"},
    "TEST": {"INTERVIEW", "SELECTED", "REJECTED"},
    "SELECTED": {"REJECTED"},
    "REJECTED": {"RECEIVED"},
    "HIRED": set(),
}


class RecruitmentError(Exception):
    pass


def submit_need(need, user):
    if need.status not in ("DRAFT", "MODIFICATION"):
        raise RecruitmentError("This need has already been submitted.")
    need.status = "SUBMITTED"
    need.save(update_fields=["status"])
    start_approval(need, "RECRUITMENT_NEED", user)
    need.refresh_from_db()
    return need


def publish_offer(offer):
    if offer.need is not None and offer.need.status != "APPROVED":
        raise RecruitmentError("The recruitment need is not approved.")
    offer.status = "PUBLISHED"
    offer.published_at = timezone.now()
    offer.save(update_fields=["status", "published_at"])
    return offer


def receive(application):
    ApplicationEvent.objects.create(
        application=application, stage="RECEIVED", comment="Application received"
    )
    notify(
        users_with_roles(User.Roles.HR_MANAGER, User.Roles.HR_OFFICER),
        f"New application: {application.full_name}",
        application.offer.title if application.offer else "Spontaneous application",
        "/recruitment",
        "INFO",
    )
    return application


def move(application, stage, user, comment=""):
    """BN-24: follow the application through the stages."""
    if stage not in NEXT_STAGES.get(application.stage, set()):
        raise RecruitmentError(
            f"An application cannot go from {application.get_stage_display()} to {stage}."
        )
    application.stage = stage
    if stage == "REJECTED" and application.score and application.score >= 50:
        application.in_pool = True  # BN-27: good profiles kept for future needs
    application.save(update_fields=["stage", "in_pool"])
    ApplicationEvent.objects.create(
        application=application, stage=stage, comment=comment, user=user
    )
    return application


@transaction.atomic
def hire(application, user, date_of_hire, department=None, position=None):
    """BN-25: the selected application becomes an employee record, no re-typing."""
    if application.stage != "SELECTED":
        raise RecruitmentError("Only a selected candidate can be hired.")
    if application.employee_id:
        raise RecruitmentError("This candidate has already been hired.")
    offer = application.offer
    to_complete = "To complete"
    employee = Employee.objects.create(
        surname=application.surname,
        given_names=application.given_names,
        date_of_birth=application.date_of_birth or datetime.date(1900, 1, 1),
        place_of_birth=application.place_of_birth or to_complete,
        sex=application.sex or "M",
        nationality=application.nationality or to_complete,
        marital_status=application.marital_status or "SINGLE",
        identity_document_type=application.identity_document_type or to_complete,
        identity_document_number=application.identity_document_number or to_complete,
        address=application.address or to_complete,
        phone_number=application.phone,
        personal_email=application.email,
        emergency_contact_name=to_complete,
        emergency_contact_number=to_complete,
        department=department or (offer.department if offer else None),
        position=position or (offer.position if offer else None),
        workplace=offer.location if offer else None,
        contract_type=offer.contract_type if offer else "PERMANENT",
        date_of_hire=date_of_hire,
        status="ACTIVE",
    )
    for field, label in (("cv", "Curriculum vitae"), ("cover_letter", "Cover letter")):
        document = getattr(application, field)
        if document:
            EmployeeDocument.objects.create(
                employee=employee, document_type="OTHER", name=label, file=document.name
            )
    EmployeeHistory.objects.create(
        employee=employee,
        author=user,
        field_name="record",
        new_value=f"Created from the application #{application.id}",
    )
    application.employee = employee
    application.stage = "HIRED"
    application.save(update_fields=["employee", "stage"])
    ApplicationEvent.objects.create(
        application=application,
        stage="HIRED",
        user=user,
        comment=f"Employee record {employee.matriculation_number}",
    )
    create_onboarding(employee, date_of_hire)
    if (
        offer
        and offer.need
        and offer.need.offers.filter(applications__stage="HIRED").count()
        >= offer.need.number_of_posts
    ):
        offer.need.status = "FILLED"
        offer.need.save(update_fields=["status"])
    return employee


def create_onboarding(employee, start):
    from notifications.services import line_manager_of

    tasks = []
    for title, role, days in ONBOARDING_CHECKLIST:
        if role == User.Roles.HEAD_OF_DEPARTMENT:
            responsible = line_manager_of(employee)
        else:
            responsible = next(iter(users_with_roles(role)), None)
        tasks.append(
            OnboardingTask.objects.create(
                employee=employee,
                title=title,
                responsible=responsible,
                due_date=start + datetime.timedelta(days=days),
            )
        )
        if responsible:
            notify(
                responsible,
                f"Onboarding of {employee.full_name}: {title}",
                f"To do by {start + datetime.timedelta(days=days):%d/%m/%Y}.",
                "/recruitment#onboarding",
                "INFO",
            )
    return tasks
