from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from django.core.management.base import CommandError
from django.db import transaction

from hub_platform.ai import documents as document_service
from hub_platform.ai import indexing
from hub_platform.ai.models import (
    DocumentScope,
    InclusionMode,
    KnowledgeCategory,
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    PromptCategory,
    PromptDocument,
    PromptDocumentVersion,
)
from hub_platform.products.models import Product

DocumentKind = Literal["prompt", "knowledge"]
_SECTION_RE = re.compile(r"^===\s*(?P<code>[a-z0-9-]+)\s*===\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ContentSpec:
    kind: DocumentKind
    title: str
    category: str
    product_code: str | None = None
    inclusion_mode: str = InclusionMode.RETRIEVAL


@dataclass(frozen=True)
class ImportResult:
    prompts_created: int = 0
    prompt_versions_created: int = 0
    knowledge_created: int = 0
    knowledge_versions_created: int = 0
    fragments_created: int = 0
    skipped_sections: int = 0

    def add(self, other: ImportResult) -> ImportResult:
        return ImportResult(
            prompts_created=self.prompts_created + other.prompts_created,
            prompt_versions_created=self.prompt_versions_created + other.prompt_versions_created,
            knowledge_created=self.knowledge_created + other.knowledge_created,
            knowledge_versions_created=self.knowledge_versions_created
            + other.knowledge_versions_created,
            fragments_created=self.fragments_created + other.fragments_created,
            skipped_sections=self.skipped_sections + other.skipped_sections,
        )


PROMPT_CATEGORY_BY_PREFIX = {
    "system": PromptCategory.SYSTEM,
    "qualify": PromptCategory.QUALIFICATION,
    "sales": PromptCategory.SALES_BEHAVIOR,
    "handoff": PromptCategory.OPERATOR_HANDOFF,
}

KNOWLEDGE_CATEGORY_BY_SUFFIX = {
    "overview": KnowledgeCategory.OVERVIEW,
    "products": KnowledgeCategory.OVERVIEW,
    "audience": KnowledgeCategory.AUDIENCE,
    "tariffs": KnowledgeCategory.COMMERCIAL,
    "catalog": KnowledgeCategory.COMMERCIAL,
    "technical": KnowledgeCategory.TECHNICAL,
    "faq": KnowledgeCategory.FAQ,
    "objections": KnowledgeCategory.OBJECTIONS,
    "limitations": KnowledgeCategory.LIMITATIONS,
}

MANDATORY_KNOWLEDGE_CODES = {
    "company-overview",
    "company-products",
    "foxray-overview",
    "foxray-tariffs",
    "firepage-overview",
    "firepage-catalog",
}

PRODUCT_CODE_BY_PREFIX = {
    "foxray": "foxray",
    "firepage": "firepage",
}

CONTENT_SOURCES = (
    "content/ai-content-company-filled.md",
    "content/ai-content-firepage-filled.md",
    "content/ai-content-foxray-filled.md",
)


def parse_filled_content(text: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        code = match.group("code")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections[code] = content
    return sections


def infer_content_spec(code: str) -> ContentSpec | None:
    parts = code.split("-")
    if len(parts) < 2:
        return None
    prompt_category = PROMPT_CATEGORY_BY_PREFIX.get(parts[0])
    product_code = PRODUCT_CODE_BY_PREFIX.get(parts[-1])
    if prompt_category:
        return ContentSpec(
            kind="prompt",
            title=code,
            category=prompt_category,
            product_code=product_code,
        )
    knowledge_category = KNOWLEDGE_CATEGORY_BY_SUFFIX.get(parts[-1])
    if knowledge_category is None:
        return None
    return ContentSpec(
        kind="knowledge",
        title=code,
        category=knowledge_category,
        product_code=PRODUCT_CODE_BY_PREFIX.get(parts[0]),
        inclusion_mode=InclusionMode.MANDATORY
        if code in MANDATORY_KNOWLEDGE_CODES
        else InclusionMode.RETRIEVAL,
    )


def _next_version(version_model, document) -> int:
    latest = version_model.objects.filter(document=document).order_by("-version").first()
    return latest.version + 1 if latest else 1


def _latest_published(version_model, document):
    return (
        version_model.objects.filter(document=document, status="PUBLISHED")
        .order_by("-version")
        .first()
    )


def _resolve_product(*, organization, product_code: str | None) -> Product | None:
    if product_code is None:
        return None
    try:
        return Product.objects.get(organization=organization, code=product_code)
    except Product.DoesNotExist as error:
        raise CommandError(
            f"Product '{product_code}' is required before importing AI content"
        ) from error


@transaction.atomic
def _import_prompt(
    *, organization, author, code: str, content: str, spec: ContentSpec
) -> ImportResult:
    product = _resolve_product(organization=organization, product_code=spec.product_code)
    scope = DocumentScope.PRODUCT if product else DocumentScope.GLOBAL
    document, created = PromptDocument.objects.update_or_create(
        organization=organization,
        product=product,
        code=code,
        defaults={
            "title": spec.title,
            "category": spec.category,
            "scope": scope,
            "is_enabled": True,
        },
    )
    latest = _latest_published(PromptDocumentVersion, document)
    if latest and latest.content == content:
        return ImportResult(prompts_created=int(created))
    version = PromptDocumentVersion.objects.create(
        document=document,
        version=_next_version(PromptDocumentVersion, document),
        content=content,
        created_by=author,
    )
    document_service.publish_version(version=version)
    return ImportResult(prompts_created=int(created), prompt_versions_created=1)


@transaction.atomic
def _import_knowledge(
    *, organization, author, code: str, content: str, spec: ContentSpec
) -> ImportResult:
    product = _resolve_product(organization=organization, product_code=spec.product_code)
    scope = DocumentScope.PRODUCT if product else DocumentScope.GLOBAL
    document, created = KnowledgeDocument.objects.update_or_create(
        organization=organization,
        product=product,
        code=code,
        defaults={
            "title": spec.title,
            "category": spec.category,
            "scope": scope,
            "is_enabled": True,
            "inclusion_mode": spec.inclusion_mode,
        },
    )
    latest = _latest_published(KnowledgeDocumentVersion, document)
    if latest and latest.content == content:
        return ImportResult(knowledge_created=int(created))
    version = KnowledgeDocumentVersion.objects.create(
        document=document,
        version=_next_version(KnowledgeDocumentVersion, document),
        content=content,
        created_by=author,
    )
    document_service.publish_version(version=version)
    fragments = indexing.reindex_knowledge_version(version)
    return ImportResult(
        knowledge_created=int(created),
        knowledge_versions_created=1,
        fragments_created=len(fragments),
    )


def ensure_channel_system_prompts(*, organization, author) -> ImportResult:
    from hub_platform.channels.models import Channel

    result = ImportResult()
    for channel in Channel.objects.filter(organization=organization).select_related("product"):
        if not channel.system_prompt.strip():
            continue
        code = f"system-{channel.product.code}" if channel.product_id else "system-edevs"
        product = channel.product if channel.product_id else None
        if PromptDocument.objects.filter(
            organization=organization, product=product, code=code
        ).exists():
            continue
        document = PromptDocument.objects.create(
            organization=organization,
            product=product,
            code=code,
            title=code,
            category=PromptCategory.SYSTEM,
            scope=DocumentScope.PRODUCT if product else DocumentScope.GLOBAL,
            is_enabled=True,
        )
        version = PromptDocumentVersion.objects.create(
            document=document,
            version=1,
            content=channel.system_prompt,
            created_by=author,
        )
        document_service.publish_version(version=version)
        result = result.add(ImportResult(prompts_created=1, prompt_versions_created=1))
    return result


def import_ai_content(*, base_dir: Path, organization, author) -> ImportResult:
    result = ImportResult()
    for relative_path in CONTENT_SOURCES:
        path = base_dir / relative_path
        if not path.exists():
            continue
        for code, content in parse_filled_content(path.read_text(encoding="utf-8")).items():
            spec = infer_content_spec(code)
            if spec is None:
                result = result.add(ImportResult(skipped_sections=1))
                continue
            if spec.kind == "prompt":
                section_result = _import_prompt(
                    organization=organization,
                    author=author,
                    code=code,
                    content=content,
                    spec=spec,
                )
            else:
                section_result = _import_knowledge(
                    organization=organization,
                    author=author,
                    code=code,
                    content=content,
                    spec=spec,
                )
            result = result.add(section_result)
    return result
