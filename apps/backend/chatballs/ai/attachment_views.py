from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.ai.models import KnowledgeAttachment
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import attachment_route
from chatballs.tenancy.lookup import load_organization


class AttachmentDownloadView(APIView):
    # Публичная ссылка защищена непредсказуемым UUID и scoped resource lookup.
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request, public_id) -> FileResponse:
        route = attachment_route(str(public_id))
        if route is None:
            raise Http404
        organization = load_organization(route.organization_id)
        if organization is None:
            raise Http404
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            attachment = KnowledgeAttachment.objects.filter(
                id=route.resource_id,
                public_id=public_id,
                organization=organization,
                knowledge__organization=organization,
            ).first()
            if attachment is None:
                raise Http404
            opened_file = attachment.file.open("rb")
            original_name = attachment.original_name
        return FileResponse(opened_file, as_attachment=True, filename=original_name)
