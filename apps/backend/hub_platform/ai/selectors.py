from django.db.models import QuerySet

from hub_platform.ai.models import AIAgent


def agents_for_organization(organization_id: int) -> QuerySet[AIAgent]:
    return (
        AIAgent.objects.select_related("product")
        .filter(product__organization_id=organization_id)
        .order_by("product__name")
    )


def agent_for_organization(*, organization_id: int, agent_id: int) -> AIAgent:
    return agents_for_organization(organization_id).get(id=agent_id)
