"""HTTP permissions and transport for shared storage commands."""
from rest_framework.views import APIView

from chatballs.identity.command_http import command_response
from chatballs.identity.instance_access import InstanceSettingsPermission, IsInstanceAdmin
from chatballs.tenancy import storage_commands as commands
from chatballs.tenancy.storage_commands import STORAGE_MIGRATION_REQUESTED  # noqa: F401
from chatballs.tenancy.storage_payloads import storage_payload  # noqa: F401


class StorageSettingsView(APIView):
    permission_classes = [InstanceSettingsPermission]

    def get(self, request):
        return command_response(commands.read(request.user))

    def patch(self, request):
        return command_response(commands.update(request.user, request.data, request=request))


class StorageCheckView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request):
        return command_response(commands.check(request.user, request.data, request=request))


class StorageMigrateView(APIView):
    permission_classes = [IsInstanceAdmin]

    def post(self, request):
        return command_response(commands.migrate(request.user, request=request))
