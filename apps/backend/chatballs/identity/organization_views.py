"""Authenticated creation retains its global domain permission checks."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from chatballs.identity import organization_commands as commands
from chatballs.identity.command_http import command_response


class OrganizationCreateOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return command_response(commands.options(request.user))


class OrganizationCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        return command_response(commands.create(request.user, request.data))
