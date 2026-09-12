from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.notifications.binding import deep_link, issue_binding_code, notifier_integrations
from chatballs.notifications.models import MessengerBinding, NotificationRead, NotificationType
from chatballs.notifications.selectors import unread_for, visible_for
from chatballs.notifications.serializers import notification_payload
from chatballs.notifications.services import TYPE_META, mark_read

_LIST_LIMIT = 50


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        items = list(visible_for(request.tenant_context)[:_LIST_LIMIT])
        read_ids = set(
            NotificationRead.objects.filter(user=request.user, notification__in=items).values_list("notification_id", flat=True)
        )
        return Response(
            {
                "items": [notification_payload(n, unread=n.id not in read_ids) for n in items],
                "unreadCount": unread_for(request.tenant_context).count(),
            }
        )


class MessengerBindingListView(APIView):
    """Сервисные боты организации + статус привязки текущего сотрудника."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        bindings = {
            binding.integration_id: binding
            for binding in MessengerBinding.objects.filter(
                user=request.user,
                integration__organization=request.tenant_context.organization,
            )
        }
        items = []
        for integration in notifier_integrations(request.tenant_context):
            binding = bindings.get(integration.id)
            items.append(
                {
                    "integrationId": integration.id,
                    "provider": integration.provider,
                    "name": integration.name,
                    "botUsername": integration.config.get("bot_username", ""),
                    "bound": binding is not None,
                    "pushTypes": binding.push_types if binding else [],
                }
            )
        # Реестр типов для чекбоксов в профиле (порядок — как в TYPE_META).
        available = [{"code": code, "label": t(meta["label"])} for code, meta in TYPE_META.items()]
        return Response({"items": items, "availableTypes": available})


class MessengerBindingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _integration(self, request: Request, integration_id: int):
        return notifier_integrations(request.tenant_context).filter(id=integration_id).first()

    def post(self, request: Request, integration_id: int) -> Response:
        """Выдать одноразовый код привязки и deep-link на бота."""
        integration = self._integration(request, integration_id)
        if integration is None:
            return Response({"detail": t("profile.notification_bot_not_found")}, status=404)
        binding_code = issue_binding_code(
            context=request.tenant_context, integration=integration
        )
        return Response(
            {
                "code": binding_code.code,
                "deepLink": deep_link(integration, binding_code.code),
                "expiresAt": binding_code.expires_at.isoformat(),
            },
            status=201,
        )

    def patch(self, request: Request, integration_id: int) -> Response:
        """Обновить типы уведомлений, доставляемые в мессенджер."""
        binding = MessengerBinding.objects.filter(user=request.user, integration_id=integration_id).first()
        if binding is None:
            return Response({"detail": t("profile.link_not_found")}, status=404)
        types = request.data.get("pushTypes")
        if not isinstance(types, list):
            return Response({"detail": t("notifications.push_types_list")}, status=400)
        binding.push_types = [code for code in types if code in NotificationType.values]
        binding.save(update_fields=["push_types"])
        return Response({"pushTypes": binding.push_types})

    def delete(self, request: Request, integration_id: int) -> Response:
        MessengerBinding.objects.filter(user=request.user, integration_id=integration_id).delete()
        return Response({"ok": True})


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if request.data.get("all"):
            mark_read(context=request.tenant_context, all_unread=True)
        else:
            ids = request.data.get("ids")
            if not isinstance(ids, list):
                return Response({"detail": t("notifications.ids_list_or_all")}, status=400)
            mark_read(context=request.tenant_context, ids=[i for i in ids if isinstance(i, int)])
        return Response({"unreadCount": unread_for(request.tenant_context).count()})
