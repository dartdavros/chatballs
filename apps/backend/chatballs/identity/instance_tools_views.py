"""HTTP surface for the installation network policy."""
from rest_framework.views import APIView

from chatballs.identity import instance_tools_commands as commands
from chatballs.identity.command_http import command_response
from chatballs.identity.instance_access import IsInstanceAdmin
from chatballs.identity.instance_tools_commands import tools_network_payload  # noqa: F401


class InstanceToolsNetworkView(APIView):
    permission_classes = [IsInstanceAdmin]

    def get(self, request):
        return command_response(commands.read(request.user))

    def patch(self, request):
        return command_response(commands.update(request.user, request.data, request=request))
