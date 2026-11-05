"""Update API retains its permissions and uses common domain commands."""
from rest_framework.views import APIView

from chatballs.identity.command_http import command_response
from chatballs.identity.instance_access import InstanceSettingsPermission, IsInstanceAdmin
from chatballs.updates import commands


class UpdateStateView(APIView):
    permission_classes = [InstanceSettingsPermission]

    def get(self, request):
        return command_response(commands.read(request.user, request=request))


class UpdateCheckView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request):
        return command_response(commands.check(request.user, request=request))


class UpdateInstallView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request):
        return command_response(commands.install(request.user, request=request))
