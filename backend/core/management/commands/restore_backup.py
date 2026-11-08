from django.core.management.base import BaseCommand, CommandError

from core.backups import backup_dir, check_backup, restore_backup


class Command(BaseCommand):
    help = "BN-183: check a backup, then restore it with --confirm (replaces ALL current data)."

    def add_arguments(self, parser):
        parser.add_argument(
            "name", help="File name of the backup (see the backups folder)."
        )
        parser.add_argument(
            "--confirm", action="store_true", help="Really restore after the check."
        )

    def handle(self, *args, name=None, confirm=False, **options):
        path = backup_dir() / name
        try:
            report = check_backup(path)
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(
            f"{report['objects']} objects, {report['media_files']} documents – archive valid."
        )
        if not confirm:
            self.stdout.write(
                "Check only. Add --confirm to restore (the current data will be replaced)."
            )
            return
        restore_backup(path)
        self.stdout.write(self.style.SUCCESS("Backup restored."))
