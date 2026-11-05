from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.ratings import queries
from chatballs.ratings.card import conversation_card
from chatballs.ratings.settings_service import settings_payload, update_settings


class RatingSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(queries.settings(request.tenant_context))

    def patch(self, request):
        return Response(settings_payload(update_settings(request.tenant_context, request.data)))


class ProtectedRatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response


class RatingResultsView(ProtectedRatingsView):
    def get(self, request):
        return Response(queries.results(request.tenant_context, request.query_params))


class ConversationRatingsView(ProtectedRatingsView):
    def get(self, request, conversation_id):
        return Response(conversation_card(request.tenant_context, conversation_id))
