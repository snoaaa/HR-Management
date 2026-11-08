from django.core.management.base import BaseCommand

from core.backups import create_backup


class Command(BaseCommand):
    help = "BN-183: back up the data and the documents (schedule it every day)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-media", action="store_true", help="Data only, without the documents."
        )

    def handle(self, *args, no_media=False, **options):
        path = create_backup(include_media=not no_media)
        self.stdout.write(self.style.SUCCESS(f"Backup created: {path}"))
