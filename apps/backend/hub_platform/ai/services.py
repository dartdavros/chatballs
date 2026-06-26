from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai import releases as release_service
from hub_platform.ai.models import (
    AIAgent,
    DocumentStatus,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    PromptCategory,
    PromptDocument,
    PromptDocumentVersion,
)
from hub_platform.products.models import Product


@dataclass(frozen=True)
class AgentInput:
    name: str
    model: str
    model_params: dict
    allowed_tools: list
    limits: dict


@dataclass(frozen=True)
class AgentCreateInput:
    product_code: str
    model: str
    system_prompt: str
    knowledge_document_ids: list[int]


START_PROMPTS: tuple[tuple[str, str, str], ...] = (
    ("system", "Системный prompt", PromptCategory.SYSTEM),
    ("qualification", "Квалификация", PromptCategory.QUALIFICATION),
    ("sales-behavior", "Поведение в продаже", PromptCategory.SALES_BEHAVIOR),
    ("operator-handoff", "Передача оператору", PromptCategory.OPERATOR_HANDOFF),
)


def _next_prompt_version(document: PromptDocument) -> int:
    latest = document.versions.order_by("-version").first()
    return latest.version + 1 if latest else 1


def _create_prompt_versions(*, product: Product, author, system_prompt: str) -> list[PromptDocumentVersion]:
    versions = []
    for code, title, category in START_PROMPTS:
        document, _ = PromptDocument.objects.get_or_create(
            product=product,
            code=code,
            defaults={"title": title, "category": category},
        )
        content = system_prompt if category == PromptCategory.SYSTEM else ""
        versions.append(
            PromptDocumentVersion.objects.create(
                document=document,
                version=_next_prompt_version(document),
                content=content,
                status=DocumentStatus.DRAFT,
                created_by=author,
            )
        )
    return versions


def _selected_knowledge_versions(*, product: Product, document_ids: list[int]) -> list[KnowledgeDocumentVersion]:
    documents = KnowledgeDocument.objects.filter(product=product, id__in=document_ids, is_enabled=True).prefetch_related("versions")
    if documents.count() != len(set(document_ids)):
        raise ValidationError({"knowledgeDocumentIds": "Unknown knowledge document"})
    versions = []
    for document in documents:
        version = document.versions.order_by("-version").first()
        if version is None:
            raise ValidationError({"knowledgeDocumentIds": "Knowledge document has no versions"})
        versions.append(version)
    return versions


@transaction.atomic
def create_agent(*, organization, author, data: AgentCreateInput) -> tuple[AIAgent, object]:
    if not data.product_code:
        raise ValidationError({"product": "Product is required"})
    if not data.model:
        raise ValidationError({"model": "Model is required"})
    if not data.knowledge_document_ids:
        raise ValidationError({"knowledgeDocumentIds": "At least one knowledge document is required"})
    try:
        product = Product.objects.get(organization=organization, code=data.product_code)
    except Product.DoesNotExist as error:
        raise ValidationError({"product": "Product not found"}) from error
    if AIAgent.objects.filter(product=product).exists():
        raise ValidationError({"product": "Product already has an AI agent"})

    agent = AIAgent.objects.create(
        product=product,
        name=f"{product.name} Sales",
        is_active=False,
        model=data.model,
    )
    knowledge_versions = _selected_knowledge_versions(product=product, document_ids=data.knowledge_document_ids)
    prompt_versions = _create_prompt_versions(product=product, author=author, system_prompt=data.system_prompt)
    release = release_service.create_initial_draft_release(
        product=product,
        author=author,
        model=agent.model,
        model_params=agent.model_params,
        allowed_tools=agent.allowed_tools,
        limits=agent.limits,
        knowledge_versions=knowledge_versions,
        prompt_versions=prompt_versions,
    )
    return agent, release


def update_agent(*, agent: AIAgent, data: AgentInput) -> AIAgent:
    agent.name = data.name
    agent.model = data.model
    agent.model_params = data.model_params
    agent.allowed_tools = data.allowed_tools
    agent.limits = data.limits
    agent.save(update_fields=["name", "model", "model_params", "allowed_tools", "limits", "updated_at"])
    return agent


def set_agent_active(*, agent: AIAgent, is_active: bool) -> AIAgent:
    agent.is_active = is_active
    agent.save(update_fields=["is_active", "updated_at"])
    return agent
