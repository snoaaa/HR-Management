from django.core.management.base import BaseCommand

from contracts.services import apply_due_terminations
from notifications.alerts import run_alerts


class Command(BaseCommand):
    help = (
        "Daily job: closes the contracts whose end is reached and sends the "
        "deadline alerts (contracts, trial periods, documents, retirement, payroll)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--no-backup", action="store_true")

    def handle(self, *args, **options):
        closed = apply_due_terminations()
        from careers.services import apply_due_acts

        applied = apply_due_acts()
        sent = run_alerts()
        from notifications.services import escalate_overdue
        from reports.services import send_scheduled_reports

        escalated = escalate_overdue()
        reports = send_scheduled_reports()
        from core.models import get_setting

        if get_setting("AUTO_BACKUP", "true").lower() == "true" and not options.get(
            "no_backup"
        ):
            from core.backups import create_backup

            self.stdout.write(f"Backup: {create_backup()}")
        self.stdout.write(
            f"{applied} career act(s) applied or ended, {escalated} request(s) escalated, "
            f"{reports} report(s) sent."
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(closed)} contract(s) closed, {sent} notification(s) sent."
            )
        )
