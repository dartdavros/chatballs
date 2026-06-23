from django.db.models import QuerySet

from hub_platform.ai.models import AIAgent, ProductAIRelease


def agents_for_organization(organization_id: int) -> QuerySet[AIAgent]:
    return (
        AIAgent.objects.select_related("product")
        .filter(product__organization_id=organization_id)
        .order_by("product__name")
    )


def agent_for_organization(*, organization_id: int, agent_id: int) -> AIAgent:
    return agents_for_organization(organization_id).get(id=agent_id)


def documents_for_organization(document_model, organization_id: int, product_code: str | None = None) -> QuerySet:
    queryset = (
        document_model.objects.select_related("product")
        .prefetch_related("versions")
        .filter(product__organization_id=organization_id)
    )
    if product_code:
        queryset = queryset.filter(product__code=product_code)
    return queryset.order_by("product__name", "category", "code")


def document_for_organization(document_model, *, organization_id: int, document_id: int):
    return documents_for_organization(document_model, organization_id).get(id=document_id)


def releases_for_organization(organization_id: int, product_code: str | None = None) -> QuerySet[ProductAIRelease]:
    queryset = (
        ProductAIRelease.objects.select_related("product")
        .prefetch_related(
            "knowledge_versions__knowledge_version__document",
            "prompt_versions__prompt_version__document",
        )
        .filter(product__organization_id=organization_id)
    )
    if product_code:
        queryset = queryset.filter(product__code=product_code)
    return queryset.order_by("product__name", "-version")


def release_for_organization(*, organization_id: int, release_id: int) -> ProductAIRelease:
    return releases_for_organization(organization_id).get(id=release_id)
