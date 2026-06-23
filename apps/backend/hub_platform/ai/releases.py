from django.db import transaction
from django.utils import timezone

from hub_platform.ai.models import (
    DocumentStatus,
    KnowledgeDocumentVersion,
    ProductAIRelease,
    PromptDocumentVersion,
    ReleaseKnowledgeVersion,
    ReleasePromptVersion,
    ReleaseStatus,
)


def _next_version(product) -> int:
    last = ProductAIRelease.objects.filter(product=product).order_by("-version").first()
    return last.version + 1 if last is not None else 1


@transaction.atomic
def _create_release(*, product, author, model, model_params, allowed_tools, limits, retrieval_index_version, notes, knowledge_versions, prompt_versions) -> ProductAIRelease:
    release = ProductAIRelease.objects.create(
        product=product,
        version=_next_version(product),
        status=ReleaseStatus.DRAFT,
        model=model,
        model_params=model_params,
        allowed_tools=allowed_tools,
        limits=limits,
        retrieval_index_version=retrieval_index_version,
        notes=notes,
        created_by=author,
    )
    ReleaseKnowledgeVersion.objects.bulk_create(
        [ReleaseKnowledgeVersion(release=release, knowledge_version=version) for version in knowledge_versions]
    )
    ReleasePromptVersion.objects.bulk_create(
        [ReleasePromptVersion(release=release, prompt_version=version) for version in prompt_versions]
    )
    return release


def create_draft_release(*, product, author, notes: str = "") -> ProductAIRelease:
    # Снимок текущей конфигурации агента + опубликованных версий включённых документов.
    agent = product.ai_agent
    knowledge_versions = KnowledgeDocumentVersion.objects.filter(
        document__product=product, document__is_enabled=True, status=DocumentStatus.PUBLISHED
    )
    prompt_versions = PromptDocumentVersion.objects.filter(
        document__product=product, document__is_enabled=True, status=DocumentStatus.PUBLISHED
    )
    return _create_release(
        product=product,
        author=author,
        model=agent.model,
        model_params=agent.model_params,
        allowed_tools=agent.allowed_tools,
        limits=agent.limits,
        retrieval_index_version="",
        notes=notes,
        knowledge_versions=list(knowledge_versions),
        prompt_versions=list(prompt_versions),
    )


@transaction.atomic
def publish_release(*, release: ProductAIRelease) -> ProductAIRelease:
    ProductAIRelease.objects.filter(product=release.product, status=ReleaseStatus.PUBLISHED).exclude(
        pk=release.pk
    ).update(status=ReleaseStatus.ARCHIVED, published_at=timezone.now())
    release.status = ReleaseStatus.PUBLISHED
    release.published_at = timezone.now()
    release.save(update_fields=["status", "published_at"])
    return release


def rollback_to_release(*, product, source: ProductAIRelease, author) -> ProductAIRelease:
    # Откат создаёт новый черновик из снимка старого release (ADR-HUB-0007).
    return _create_release(
        product=product,
        author=author,
        model=source.model,
        model_params=source.model_params,
        allowed_tools=source.allowed_tools,
        limits=source.limits,
        retrieval_index_version=source.retrieval_index_version,
        notes=f"Откат к версии v{source.version}",
        knowledge_versions=[link.knowledge_version for link in source.knowledge_versions.all()],
        prompt_versions=[link.prompt_version for link in source.prompt_versions.all()],
    )
