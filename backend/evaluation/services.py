"""Business rules of M-10."""

import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from employees.models import Employee
from notifications.services import line_manager_of, notify, users_with_roles
from users.models import User

from .models import Evaluation

ZERO = Decimal("0")


class EvaluationError(Exception):
    pass


@transaction.atomic
def open_campaign(campaign, user):
    """Create an evaluation for each employee of the population (BN-82)."""
    if campaign.status != "DRAFT":
        raise EvaluationError("Only a draft campaign can be opened.")
    if not campaign.criteria:
        raise EvaluationError("Define the evaluation form (criteria) first.")
    employees = Employee.objects.filter(status="ACTIVE")
    departments = list(campaign.departments.all())
    if departments:
        employees = employees.filter(department__in=departments)
    hr_manager = next(iter(users_with_roles(User.Roles.HR_MANAGER)), None)
    created = 0
    for employee in employees:
        evaluator = line_manager_of(employee) or hr_manager
        _, was_created = Evaluation.objects.get_or_create(
            campaign=campaign, employee=employee, defaults={"evaluator": evaluator}
        )
        created += was_created
        if was_created and employee.user:
            notify(
                employee.user,
                f"Evaluation campaign: {campaign.name}",
                f"Please complete your self-evaluation before {campaign.end_date:%d/%m/%Y}.",
                "/my/evaluations",
                "REQUEST",
            )
    campaign.status = "OPEN"
    campaign.save(update_fields=["status"])
    return created


def _check_scores(campaign, scores):
    codes = {c["code"] for c in campaign.criteria}
    for code, value in (scores or {}).items():
        if code not in codes:
            raise EvaluationError(f"Unknown criterion {code}.")
        try:
            number = Decimal(str(value))
        except Exception:
            raise EvaluationError(f"Invalid score for {code}.")
        if not (0 <= number <= campaign.scale_max):
            raise EvaluationError(f"The scores are between 0 and {campaign.scale_max}.")
    missing = codes - set((scores or {}).keys())
    if missing:
        raise EvaluationError(f"Score every criterion ({', '.join(sorted(missing))}).")


def submit_self(evaluation, scores, comment):
    if evaluation.status != "SELF_ASSESSMENT" or evaluation.campaign.status != "OPEN":
        raise EvaluationError("The self-evaluation is closed.")
    _check_scores(evaluation.campaign, scores)
    evaluation.self_scores = scores
    evaluation.self_comment = comment
    evaluation.status = "MANAGER_ASSESSMENT"
    evaluation.save()
    if evaluation.evaluator:
        notify(
            evaluation.evaluator,
            f"Evaluation to complete: {evaluation.employee.full_name}",
            "",
            f"/evaluation/{evaluation.id}",
            "REQUEST",
        )
    return evaluation


def compute_score(evaluation):
    """BN-84: weighted criteria (manager) and weighted objectives, out of 100."""
    campaign = evaluation.campaign
    total_weight = sum(
        Decimal(str(c.get("weight", 1))) for c in campaign.criteria
    ) or Decimal(1)
    criteria = (
        sum(
            Decimal(str(evaluation.manager_scores.get(c["code"], 0)))
            * Decimal(str(c.get("weight", 1)))
            for c in campaign.criteria
        )
        / total_weight
        / Decimal(campaign.scale_max)
        * 100
    )
    objectives = list(evaluation.objectives.all())
    if not objectives:
        return criteria.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    weights = sum(Decimal(o.weight) for o in objectives) or Decimal(1)
    achieved = sum(min(o.score, Decimal(120)) * o.weight for o in objectives) / weights
    share = Decimal(campaign.objectives_weight) / 100
    score = criteria * (1 - share) + achieved * share
    return score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def submit_manager(evaluation, user, data):
    if evaluation.status != "MANAGER_ASSESSMENT":
        raise EvaluationError("The evaluation is not waiting for the manager.")
    _check_scores(evaluation.campaign, data.get("manager_scores"))
    for field in (
        "manager_scores",
        "manager_comment",
        "strengths",
        "improvements",
        "actions_decided",
        "proposal",
        "bonus_amount",
        "training_subject",
    ):
        if field in data:
            setattr(evaluation, field, data[field])
    if evaluation.proposal == "BONUS" and not evaluation.bonus_amount:
        raise EvaluationError("Enter the amount of the performance bonus.")
    evaluation.final_score = compute_score(evaluation)
    evaluation.status = "COMPLETED"
    evaluation.save()
    if evaluation.employee.user:
        notify(
            evaluation.employee.user,
            f"Evaluation completed: {evaluation.campaign.name}",
            f"Final score: {evaluation.final_score}/100.",
            "/my/evaluations",
            "INFO",
        )
    return evaluation


@transaction.atomic
def validate(evaluation, user):
    """HR validation; the proposal is transmitted (BN-85)."""
    if evaluation.status != "COMPLETED":
        raise EvaluationError("Only a completed evaluation can be validated.")
    evaluation.status = "VALIDATED"
    evaluation.validated_at = timezone.now()
    apply_proposal(evaluation, user)
    evaluation.save()
    return evaluation


def apply_proposal(evaluation, user):
    if evaluation.proposal_applied or evaluation.proposal == "NONE":
        return None
    result = None
    if evaluation.proposal == "BONUS":
        from payroll.models import SalaryElement, VariableInput
        from payroll.services import open_period

        today = timezone.now().date()
        period = open_period(today.year, today.month, user)
        if period.is_locked:
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            period = open_period(next_month.year, next_month.month, user)
        element = SalaryElement.objects.filter(code="PERFORMANCE").first()
        if element is None:
            raise EvaluationError("The salary element PERFORMANCE is missing.")
        result = VariableInput.objects.create(
            period=period,
            employee=evaluation.employee,
            element=element,
            amount=evaluation.bonus_amount,
            source="MANUAL",
            comment=f"Performance bonus – {evaluation.campaign.name}",
            created_by=user,
        )
    elif evaluation.proposal == "PROMOTION":
        from careers.models import CareerAct

        result = CareerAct.objects.create(
            employee=evaluation.employee,
            act_type="PROMOTION",
            effective_date=timezone.now().date(),
            reason=f"Proposed by the evaluation {evaluation.campaign.name} (score {evaluation.final_score}/100)",
            created_by=user,
        )
    elif evaluation.proposal == "TRAINING":
        from training.models import TrainingNeed

        result = TrainingNeed.objects.create(
            employee=evaluation.employee,
            department=evaluation.employee.department,
            subject=evaluation.training_subject
            or "Training proposed by the evaluation",
            year=evaluation.campaign.year,
            origin="EVALUATION",
            created_by=user,
        )
    evaluation.proposal_applied = True
    return result


def campaign_summary(campaign):
    """BN-86: summary of a campaign."""
    evaluations = list(
        campaign.evaluations.select_related("employee", "employee__department")
    )
    scored = [e.final_score for e in evaluations if e.final_score is not None]
    by_department = {}
    for e in evaluations:
        name = e.employee.department.name if e.employee.department else "—"
        bucket = by_department.setdefault(
            name, {"department": name, "count": 0, "scores": []}
        )
        bucket["count"] += 1
        if e.final_score is not None:
            bucket["scores"].append(e.final_score)
    return {
        "campaign": campaign.name,
        "population": len(evaluations),
        "completed": sum(
            1 for e in evaluations if e.status in ("COMPLETED", "VALIDATED")
        ),
        "validated": sum(1 for e in evaluations if e.status == "VALIDATED"),
        "average_score": round(sum(scored) / len(scored), 2) if scored else None,
        "proposals": {
            p: sum(1 for e in evaluations if e.proposal == p)
            for p, _ in Evaluation.PROPOSALS
        },
        "by_department": [
            {
                "department": b["department"],
                "count": b["count"],
                "average": (
                    round(sum(b["scores"]) / len(b["scores"]), 2)
                    if b["scores"]
                    else None
                ),
            }
            for b in by_department.values()
        ],
    }
