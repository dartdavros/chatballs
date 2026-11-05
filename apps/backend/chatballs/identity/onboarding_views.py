"""HTTP onboarding checklist uses the same services as native actions."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.identity.onboarding_services import change_onboarding, onboarding_status


class OnboardingView(APIView):
    permission_classes = [HasCapability]
    required_capability = "settings.view"

    def get(self, request):
        return Response(onboarding_status(request.tenant_context))

    def post(self, request):
        return Response(change_onboarding(request.tenant_context, request.data))
