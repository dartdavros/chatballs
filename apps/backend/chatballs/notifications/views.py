"""HTTP adapters for personal notification domain services."""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.notifications import profile_services as service


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(service.notifications(request.tenant_context))


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return Response(service.read_notifications(request.tenant_context, request.data))


class MessengerBindingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(service.bindings(request.tenant_context))


class MessengerBindingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, integration_id):
        return Response(service.create_binding_code(request.tenant_context, integration_id), status=201)

    def patch(self, request, integration_id):
        return Response(service.update_binding(request.tenant_context, integration_id, request.data.get("pushTypes")))

    def delete(self, request, integration_id):
        return Response(service.delete_binding(request.tenant_context, integration_id))


class NotificationPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, transport):
        return Response(service.notification_preference(request.tenant_context, transport))

    def patch(self, request, transport):
        return Response(service.notification_preference(request.tenant_context, transport, request.data))
