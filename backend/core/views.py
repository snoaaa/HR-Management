import re

from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.utils import log_audit_action

from .exports import export_rows
from .models import Setting
from .serializers import SettingSerializer


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role in (
            User.Roles.SYSTEM_ADMINISTRATOR,
            User.Roles.HR_MANAGER,
        )


class SettingViewSet(viewsets.ModelViewSet):
    """BN-178: configure the reference parameters of the system."""

    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]

    def perform_update(self, serializer):
        previous = serializer.instance.value
        setting = serializer.save()
        log_audit_action(
            user=self.request.user,
            action=f"Changed setting {setting.key}",
            module="Settings",
            request=self.request,
            details={"previous_value": previous, "new_value": setting.value},
        )


class TableExportView(APIView):
    """
    BN-126: any list displayed in the application, extracted as a PDF in the
    colours of the organisation or as an Excel / CSV file. The rows are those
    the user already sees on the screen (the access rights were applied when
    they were loaded).
    """

    permission_classes = [IsAuthenticated]
    MAX_ROWS = 5000

    def post(self, request):
        title = str(request.data.get("title") or "Export")[:120]
        headers = request.data.get("headers")
        rows = request.data.get("rows")
        fmt = request.data.get("file_format", "pdf")
        if fmt not in ("pdf", "xlsx", "csv"):
            return Response({"detail": "Unknown format."}, status=400)
        if not isinstance(headers, list) or not headers:
            return Response({"detail": "Give the column titles."}, status=400)
        if not isinstance(rows, list) or len(rows) > self.MAX_ROWS:
            return Response(
                {"detail": f"Give between 0 and {self.MAX_ROWS} rows."}, status=400
            )
        headers = [str(h)[:80] for h in headers]
        clean = []
        for row in rows:
            if not isinstance(row, list):
                return Response({"detail": "Each row is a list."}, status=400)
            cells = [
                (
                    c
                    if isinstance(c, (int, float)) and not isinstance(c, bool)
                    else ("" if c is None else str(c)[:500])
                )
                for c in row[: len(headers)]
            ]
            clean.append(cells + [""] * (len(headers) - len(cells)))
        filename = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "export"
        log_audit_action(
            request.user, f"Exported the list '{title}' ({fmt})", "Exports"
        )
        return export_rows(
            headers,
            clean,
            filename,
            fmt,
            title=title,
            subtitle=str(request.data.get("subtitle") or "")[:200],
        )
