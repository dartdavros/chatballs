"""Label HTTP adapters and reply-template compatibility exports."""

from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.conversations.label_services import (
    create_label,
    delete_label,
    labels_for,
    update_label,
)
from chatballs.conversations.label_services import (
    label_payload as _label_payload,
)


class LabelListView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"GET": "conversations.view", "POST": "conversations.operate"}

    def get(self, request):
        return Response({"items": [_label_payload(label) for label in labels_for(request.tenant_context)]})

    def post(self, request):
        label, created = create_label(context=request.tenant_context,
            name=request.data.get("name", ""), color=request.data.get("color", ""))
        return Response({"label": _label_payload(label)}, status=201 if created else 200)


class LabelDetailView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {"PATCH": "settings.manage", "DELETE": "settings.manage"}

    def patch(self, request, label_id):
        label = update_label(context=request.tenant_context, label_id=label_id, changes=request.data)
        return Response({"label": _label_payload(label)})

    def delete(self, request, label_id):
        delete_label(context=request.tenant_context, label_id=label_id)
        return Response(status=204)


from chatballs.conversations.template_views import (  # noqa: E402, F401
    ReplyTemplateDetailView,
    ReplyTemplateListView,
)
