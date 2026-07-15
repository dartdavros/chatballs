from django.db.models import QuerySet

from hub_platform.integrations.models import Integration
from hub_platform.tenancy.context import TenantContext


def integrations_for_context(context: TenantContext) -> QuerySet[Integration]:
    return Integration.objects.filter(organization_id=context.organization_id).select_related("channel").order_by("provider", "name")


def integration_for_context(*, context: TenantContext, integration_id: int) -> Integration:
    return Integration.objects.get(id=integration_id, organization_id=context.organization_id)
