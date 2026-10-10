from django.core.management import call_command
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.views import IsSystemAdminOrHRManager
from users.utils import log_audit_action

from . import services
from .models import ApprovalCircuit, ApprovalTask, Notification, NotificationPreference
from .serializers import (
    ApprovalCircuitSerializer,
    ApprovalTaskSerializer,
    NotificationPreferenceSerializer,
    NotificationSerializer,
)


class NotificationViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """BN-167: notification centre of the logged-in user."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") == "true":
            queryset = queryset.filter(is_read=False)
        return queryset[:200] if self.action == "list" else queryset

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({"count": count})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class PreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        return Response(NotificationPreferenceSerializer(pref).data)

    def put(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = NotificationPreferenceSerializer(pref, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ApprovalTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """Requests waiting for a decision of the logged-in user (BN-51, BN-153)."""

    serializer_class = ApprovalTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.query_params.get("scope") == "history":
            return ApprovalTask.objects.filter(decided_by=self.request.user)[:200]
        return services.tasks_for(self.request.user)

    @action(detail=True, methods=["post"])
    def decide(self, request, pk=None):
        task = ApprovalTask.objects.filter(pk=pk).first()
        if task is None or not services.can_decide(task, request.user):
            return Response(
                {"detail": "You cannot decide on this request."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            services.decide(
                task,
                request.user,
                request.data.get("decision"),
                request.data.get("comment", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        log_audit_action(
            user=request.user,
            action=f"{task.status} {task.request_type} request #{task.object_id}",
            module="Workflow",
            request=request,
            details={"task_id": task.id, "comment": task.comment},
        )
        return Response(ApprovalTaskSerializer(task).data)


class ApprovalCircuitViewSet(viewsets.ModelViewSet):
    """BN-166: approval circuits per type of request."""

    queryset = ApprovalCircuit.objects.prefetch_related("levels")
    serializer_class = ApprovalCircuitSerializer
    permission_classes = [IsSystemAdminOrHRManager]


class RunAlertsView(APIView):
    """Runs the deadline alerts immediately (also meant to be scheduled daily)."""

    permission_classes = [IsSystemAdminOrHRManager]

    def post(self, request):
        call_command("send_deadline_alerts")
        return Response({"detail": "Deadline alerts processed."})
