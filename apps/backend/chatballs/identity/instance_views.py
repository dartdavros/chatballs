"""HTTP authentication and transport for shared instance commands."""
from rest_framework.views import APIView

from chatballs.identity import instance_commands, instance_email_commands
from chatballs.identity.command_http import command_response
from chatballs.identity.instance_access import InstanceSettingsPermission, IsInstanceAdmin
from chatballs.identity.instance_payloads import instance_payload  # noqa: F401


class InstanceAddressView(APIView):
    permission_classes = [InstanceSettingsPermission]

    def get(self, request):
        return command_response(instance_commands.read(request.user))

    def patch(self, request):
        return command_response(instance_commands.update(request.user, request.data))


class InstanceEmailCheckView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request):
        return command_response(instance_email_commands.check(request.user, request.data))
