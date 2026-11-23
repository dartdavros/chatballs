"""Update API retains its permissions and uses common domain commands."""
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.identity.command_http import command_response
from chatballs.identity.instance_access import CanManagePlatform, InstanceSettingsPermission
from chatballs.updates import commands
from chatballs.updates.announcement_state import schedule_snapshot
from chatballs.updates.check_in_state import announcement_snapshot


class UpdateStateView(APIView):
    permission_classes = [InstanceSettingsPermission]

    def get(self, request):
        return command_response(commands.read(request.user, request=request))


class ServiceAnnouncementsView(APIView):
    permission_classes = [CanManagePlatform]

    def get(self, request):
        return Response(schedule_snapshot() or announcement_snapshot(), headers={"Cache-Control": "no-store"})


class UpdateCheckView(APIView):
    permission_classes = [CanManagePlatform]

    def post(self, request):
        return command_response(commands.check(request.user, request=request))


class UpdateInstallView(APIView):
    permission_classes = [CanManagePlatform]

    def post(self, request):
        return command_response(commands.install(request.user, request=request))
