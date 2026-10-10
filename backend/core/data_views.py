"""BN-179 imports and BN-183 backups through the API."""

from django.db import transaction
from django.http import FileResponse, HttpResponse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import ModulePermission, is_admin
from users.utils import log_audit_action

from . import backups, imports


class ImportView(APIView):
    """GET the template of an import, POST a file (dry_run=true by default)."""

    permission_classes = [ModulePermission]
    permission_module = "imports"
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, kind):
        kind = kind.upper()
        if kind not in imports.KINDS:
            return Response({"detail": "Unknown import."}, status=404)
        response = HttpResponse(imports.template_csv(kind), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="import-{kind.lower()}.csv"'
        )
        return response

    def post(self, request, kind):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Send the file in 'file'."}, status=400)
        dry_run = str(request.data.get("dry_run", "true")).lower() != "false"
        try:
            with transaction.atomic():
                report = imports.run_import(
                    kind.upper(), upload.name, upload.read(), request.user, dry_run
                )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        if not dry_run:
            log_audit_action(
                request.user,
                f"Imported {kind} ({report['imported']} lines)",
                "Imports",
                request,
                {"rejected": len(report["rejected"])},
            )
        return Response(report)


class BackupListView(APIView):
    """List the backups (GET) or create one now (POST)."""

    permission_classes = [ModulePermission]
    permission_module = "imports"

    def get(self, request):
        return Response(backups.list_backups())

    def post(self, request):
        path = backups.create_backup()
        log_audit_action(
            request.user, f"Created backup {path.name}", "Backups", request
        )
        return Response({"name": path.name}, status=201)


class BackupActionView(APIView):
    """check / download (GET), restore (POST with {"confirm": true})."""

    permission_classes = [ModulePermission]
    permission_module = "imports"

    def get(self, request, name, operation):
        path = backups.backup_dir() / name
        try:
            report = backups.check_backup(path)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        if operation == "download":
            log_audit_action(
                request.user, f"Downloaded backup {name}", "Backups", request
            )
            return FileResponse(path.open("rb"), as_attachment=True, filename=name)
        return Response(report)

    def post(self, request, name, operation):
        if operation != "restore" or request.data.get("confirm") is not True:
            return Response(
                {"detail": 'Send {"confirm": true} to restore.'}, status=400
            )
        if not is_admin(request.user):
            return Response(
                {"detail": "Only the system administrator restores a backup."},
                status=403,
            )
        try:
            report = backups.restore_backup(backups.backup_dir() / name)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response({"restored": True, **report})
