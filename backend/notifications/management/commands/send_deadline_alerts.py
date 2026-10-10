from django.core.management.base import BaseCommand

from contracts.services import apply_due_terminations
from notifications.alerts import run_alerts


class Command(BaseCommand):
    help = (
        "Daily job: closes the contracts whose end is reached and sends the "
        "deadline alerts (contracts, trial periods, documents, retirement, payroll)."
    )

    def handle(self, *args, **options):
        closed = apply_due_terminations()
        sent = run_alerts()
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(closed)} contract(s) closed, {sent} notification(s) sent."
            )
        )
