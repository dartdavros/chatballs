from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.notifications.binding import deep_link, issue_binding_code, notifier_integrations
from hub_platform.notifications.models import MessengerBinding, NotificationRead
from hub_platform.notifications.selectors import unread_for, visible_for
from hub_platform.notifications.serializers import notification_payload
from hub_platform.notifications.services import mark_read

_LIST_LIMIT = 50


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        items = list(visible_for(request.user)[:_LIST_LIMIT])
        read_ids = set(
            NotificationRead.objects.filter(user=request.user, notification__in=items).values_list("notification_id", flat=True)
        )
        return Response(
            {
                "items": [notification_payload(n, unread=n.id not in read_ids) for n in items],
                "unreadCount": unread_for(request.user).count(),
            }
        )


class MessengerBindingListView(APIView):
    """Сервисные боты организации + статус привязки текущего сотрудника."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        organization_id = request.user.employee_profile.organization_id
        bound_ids = set(
            MessengerBinding.objects.filter(user=request.user, integration__organization_id=organization_id)
            .values_list("integration_id", flat=True)
        )
        items = [
            {
                "integrationId": integration.id,
                "provider": integration.provider,
                "name": integration.name,
                "botUsername": integration.config.get("bot_username", ""),
                "bound": integration.id in bound_ids,
            }
            for integration in notifier_integrations(organization_id)
        ]
        return Response({"items": items})


class MessengerBindingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _integration(self, request: Request, integration_id: int):
        return notifier_integrations(request.user.employee_profile.organization_id).filter(id=integration_id).first()

    def post(self, request: Request, integration_id: int) -> Response:
        """Выдать одноразовый код привязки и deep-link на бота."""
        integration = self._integration(request, integration_id)
        if integration is None:
            return Response({"detail": "Бот уведомлений не найден"}, status=404)
        binding_code = issue_binding_code(user=request.user, integration=integration)
        return Response(
            {
                "code": binding_code.code,
                "deepLink": deep_link(integration, binding_code.code),
                "expiresAt": binding_code.expires_at.isoformat(),
            },
            status=201,
        )

    def delete(self, request: Request, integration_id: int) -> Response:
        MessengerBinding.objects.filter(user=request.user, integration_id=integration_id).delete()
        return Response({"ok": True})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if request.data.get("all"):
            mark_read(user=request.user, all_unread=True)
        else:
            ids = request.data.get("ids")
            if not isinstance(ids, list):
                return Response({"detail": "ids must be a list or use all=true"}, status=400)
            mark_read(user=request.user, ids=[i for i in ids if isinstance(i, int)])
        return Response({"unreadCount": unread_for(request.user).count()})
