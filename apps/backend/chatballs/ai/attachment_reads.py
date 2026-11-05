"""Resolve the existing public UUID protocol without crossing tenant scope."""

from chatballs.ai.models import KnowledgeAttachment
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import attachment_route
from chatballs.tenancy.lookup import load_organization


def open_attachment(public_id, *, organization_id=None):
    route = attachment_route(str(public_id))
    if route is None or organization_id is not None and route.organization_id != organization_id:
        raise KnowledgeAttachment.DoesNotExist()
    organization = load_organization(route.organization_id)
    if organization is None:
        raise KnowledgeAttachment.DoesNotExist()
    with tenant_atomic(TenantContext.for_resource(organization)):
        attachment = KnowledgeAttachment.objects.get(id=route.resource_id, public_id=public_id,
            organization=organization, knowledge__organization=organization)
        return attachment.file.open("rb"), attachment.original_name, attachment.content_type

