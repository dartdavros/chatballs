from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.notifications.models import NotificationRead
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
