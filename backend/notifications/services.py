"""
M-16 – Notifications and workflow.

notify(): BN-163 / BN-167, in-app notification and e-mail according to the
preferences of each user.

Approval engine: BN-51 / BN-166, configurable multi-level circuits with a
substitute when the approver is absent. Any model can go through a circuit
if it implements:

    approval_requester()            -> Employee who made the request
    approval_summary()              -> short text shown to approvers
    approval_link                   -> frontend path of the request
    on_approval_completed(user)
    on_approval_refused(user, comment)
    on_modification_requested(user, comment)
"""

import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from users.models import User

from .models import (
    ApprovalCircuit,
    ApprovalLevel,
    ApprovalTask,
    Notification,
    NotificationPreference,
)

logger = logging.getLogger(__name__)


def notify(users, title, message="", link="", category="INFO", dedupe_key=""):
    """Send a notification to one user or a list of users."""
    if users is None:
        return []
    if isinstance(users, User):
        users = [users]
    created = []
    for user in {u for u in users if u is not None and u.is_active}:
        if (
            dedupe_key
            and Notification.objects.filter(user=user, dedupe_key=dedupe_key).exists()
        ):
            continue
        pref = NotificationPreference.objects.filter(user=user).first()
        in_app = pref.in_app if pref else True
        by_email = pref.email if pref else True
        if in_app or dedupe_key:
            # Kept (as already read) even without the in-app channel so that
            # a deadline alert is not e-mailed again every day.
            created.append(
                Notification.objects.create(
                    user=user,
                    title=title,
                    message=message,
                    link=link,
                    category=category,
                    dedupe_key=dedupe_key,
                    is_read=not in_app,
                )
            )
        if by_email and user.email:
            try:
                send_mail(
                    f"[HRMS] {title}",
                    f"{message}\n\n{link}",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=True,
                )
            except Exception as exc:  # e-mail must never block the request
                logger.warning("Notification e-mail failed: %s", exc)
    return created


def users_with_roles(*roles):
    return list(User.objects.filter(role__in=roles, is_active=True))


def notify_roles(roles, title, message="", link="", category="INFO", dedupe_key=""):
    return notify(users_with_roles(*roles), title, message, link, category, dedupe_key)


# --------------------------------------------------------------------------
# Approval engine
# --------------------------------------------------------------------------


def line_manager_of(employee):
    """Manager of the employee's unit, going up when the employee is the manager."""
    department = employee.department if employee else None
    while department is not None:
        manager = department.manager
        if manager is not None and manager.id != employee.user_id:
            return manager
        department = department.parent
    return None


def _is_absent(user, day):
    try:
        from leave.services import is_on_leave
    except ImportError:
        return False
    return is_on_leave(user, day)


def _resolve_approver(level, requester):
    """Return (user, role) expected to decide at this level."""
    if level.approver == ApprovalLevel.LINE_MANAGER:
        user = line_manager_of(requester)
        if user is None:
            # No line manager: the HR manager decides.
            return None, User.Roles.HR_MANAGER
        if level.substitute and _is_absent(user, timezone.now().date()):
            return level.substitute, ""
        return user, ""
    if level.substitute:
        holders = users_with_roles(level.approver)
        today = timezone.now().date()
        if holders and all(_is_absent(u, today) for u in holders):
            return level.substitute, ""
    return None, level.approver


def _approvers_of(task):
    if task.approver_user:
        return [task.approver_user]
    return users_with_roles(task.approver_role)


def _create_task(target, request_type, level):
    requester = target.approval_requester()
    user, role = _resolve_approver(level, requester)
    task = ApprovalTask.objects.create(
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        request_type=request_type,
        level=level.order,
        approver_user=user,
        approver_role=role,
        summary=target.approval_summary()[:255],
    )
    notify(
        _approvers_of(task),
        f"Approval required: {task.summary}",
        "A request is waiting for your decision.",
        "/approvals",
        "APPROVAL",
    )
    return task


def _levels(request_type):
    circuit = ApprovalCircuit.objects.filter(request_type=request_type).first()
    return list(circuit.levels.all()) if circuit else []


@transaction.atomic
def start_approval(target, request_type, user=None):
    """Submit a request. Without a configured circuit it is approved at once."""
    pending_tasks(target).update(status="CANCELLED")
    levels = _levels(request_type)
    if not levels:
        target.on_approval_completed(user)
        return None
    return _create_task(target, request_type, levels[0])


def pending_tasks(target):
    return ApprovalTask.objects.filter(
        content_type=ContentType.objects.get_for_model(target),
        object_id=target.pk,
        status="PENDING",
    )


def can_decide(task, user):
    if task.status != "PENDING":
        return False
    if user.is_superuser:
        return True
    if task.approver_user_id:
        return task.approver_user_id == user.id
    return bool(task.approver_role) and user.role == task.approver_role


def tasks_for(user):
    from django.db.models import Q

    queryset = ApprovalTask.objects.filter(status="PENDING")
    if user.is_superuser:
        return queryset
    return queryset.filter(
        Q(approver_user=user) | Q(approver_user__isnull=True, approver_role=user.role)
    )


@transaction.atomic
def decide(task, user, decision, comment=""):
    """decision: APPROVED, REFUSED or MODIFICATION (BN-51)."""
    if decision not in ("APPROVED", "REFUSED", "MODIFICATION"):
        raise ValueError("Unknown decision.")
    if decision != "APPROVED" and not comment:
        raise ValueError("A reason is required to refuse or ask for a modification.")
    task.status = decision
    task.comment = comment
    task.decided_by = user
    task.decided_at = timezone.now()
    task.save()

    target = task.target
    requester = target.approval_requester()
    requester_user = requester.user if requester else None
    link = getattr(target, "approval_link", "")

    if decision == "REFUSED":
        target.on_approval_refused(user, comment)
        notify(requester_user, f"Refused: {task.summary}", comment, link, "REQUEST")
        return task
    if decision == "MODIFICATION":
        target.on_modification_requested(user, comment)
        notify(
            requester_user,
            f"Modification requested: {task.summary}",
            comment,
            link,
            "REQUEST",
        )
        return task

    next_levels = [lvl for lvl in _levels(task.request_type) if lvl.order > task.level]
    if next_levels:
        _create_task(target, task.request_type, next_levels[0])
        notify(
            requester_user,
            f"Approved at level {task.level}: {task.summary}",
            "Your request goes to the next approver.",
            link,
            "REQUEST",
        )
    else:
        target.on_approval_completed(user)
        notify(requester_user, f"Approved: {task.summary}", "", link, "REQUEST")
    return task
