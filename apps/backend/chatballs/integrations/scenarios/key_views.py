from rest_framework.response import Response

from chatballs.integrations.scenario_state.subscriptions import ScenarioExternalKey
from chatballs.integrations.scenarios.external_keys import rotate_key
from chatballs.integrations.scenarios.services import RevisionConflict
from chatballs.integrations.scenarios.views import ScenarioAPIView


class ScenarioRotateKeyView(ScenarioAPIView):
    def post(self, request, public_id, trigger_id):
        scenario = self.rows(request).select_for_update().get(public_id=public_id)
        revision = request.data.get("revision") if isinstance(request.data, dict) else None
        if type(revision) is not int or revision != scenario.revision:
            raise RevisionConflict
        try:
            payload = rotate_key(request, scenario, trigger_id)
        except ScenarioExternalKey.DoesNotExist:
            return Response(status=404)
        self.audit(request, scenario, "key_rotated")
        return Response({"externalKey": payload})
