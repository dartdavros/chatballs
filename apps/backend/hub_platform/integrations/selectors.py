from django.db.models import QuerySet

from hub_platform.integrations.models import Integration


def integrations_for_organization(organization_id: int) -> QuerySet[Integration]:
    return Integration.objects.filter(organization_id=organization_id).order_by("provider", "name")


def integration_for_organization(*, organization_id: int, integration_id: int) -> Integration:
    return Integration.objects.get(id=integration_id, organization_id=organization_id)
