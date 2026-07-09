from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from django.db import transaction

from hub_platform.ai import documents as document_service
from hub_platform.ai.models import DocumentScope, InclusionMode
from hub_platform.products.models import Product


@dataclass(frozen=True)
class ImportReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: list = field(default_factory=list)  # [{code, detail}]

    def add(self, other: "ImportReport") -> "ImportReport":
        return ImportReport(
            created=self.created + other.created,
            updated=self.updated + other.updated,
            unchanged=self.unchanged + other.unchanged,
            failed=[*self.failed, *other.failed],
        )

    def as_payload(self) -> dict:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "failed": list(self.failed),
        }


def resolve_product(*, organization, product_code: str | None) -> Product | None:
    # product_code None → глобальный скоуп (как в существующем импортёре).
    if product_code is None:
        return None
    try:
        return Product.objects.get(organization=organization, code=product_code)
    except Product.DoesNotExist as error:
        raise ValueError(f"Продукт «{product_code}» не найден") from error


def _latest_published(version_model, document):
    return (
        version_model.objects.filter(document=document, status="PUBLISHED")
        .order_by("-version")
        .first()
    )


def _next_version(version_model, document) -> int:
    latest = version_model.objects.filter(document=document).order_by("-version").first()
    return latest.version + 1 if latest else 1


@dataclass(frozen=True)
class DocInput:
    code: str
    title: str
    category: str
    content: str
    inclusion_mode: str = InclusionMode.RETRIEVAL


def import_documents(
    *,
    organization,
    author,
    document_model,
    version_model,
    product_code: str | None,
    documents: list,
    supports_inclusion: bool,
    after_publish: Callable | None = None,
) -> ImportReport:
    # Idempotent upsert по (org, product, code) + немедленная публикация.
    # Контент не меняется → unchanged (нет дубль-версий); изменился → новая published-версия.
    report = ImportReport()
    failed: list = []
    try:
        product = resolve_product(organization=organization, product_code=product_code)
    except ValueError as error:
        return ImportReport(failed=[{"code": "", "detail": str(error)}])
    scope = DocumentScope.PRODUCT if product else DocumentScope.GLOBAL

    for item in documents:
        try:
            doc = _coerce_doc(item, supports_inclusion=supports_inclusion)
        except ValueError as error:
            failed.append({"code": str(item.get("code", "")) if isinstance(item, dict) else "", "detail": str(error)})
            continue
        report = report.add(_import_one(
            organization=organization,
            author=author,
            document_model=document_model,
            version_model=version_model,
            product=product,
            scope=scope,
            doc=doc,
            supports_inclusion=supports_inclusion,
            after_publish=after_publish,
        ))
    return ImportReport(created=report.created, updated=report.updated, unchanged=report.unchanged, failed=[*failed, *report.failed])


def _coerce_doc(item, *, supports_inclusion: bool) -> DocInput:
    if not isinstance(item, dict):
        raise ValueError("документ должен быть объектом")
    code = str(item.get("code", "")).strip()
    title = str(item.get("title", "")).strip()
    category = str(item.get("category", "")).strip()
    content = str(item.get("content", ""))
    if not code or not title:
        raise ValueError("code и title обязательны")
    inclusion_mode = InclusionMode.RETRIEVAL
    if supports_inclusion and item.get("inclusionMode"):
        candidate = str(item.get("inclusionMode"))
        if candidate not in InclusionMode.values:
            raise ValueError(f"неизвестный inclusionMode: {candidate}")
        inclusion_mode = candidate
    return DocInput(code=code, title=title, category=category, content=content, inclusion_mode=inclusion_mode)


@transaction.atomic
def _import_one(
    *,
    organization,
    author,
    document_model,
    version_model,
    product,
    scope,
    doc: DocInput,
    supports_inclusion: bool,
    after_publish,
) -> ImportReport:
    defaults = {
        "title": doc.title,
        "category": doc.category,
        "scope": scope,
        "is_enabled": True,
    }
    if supports_inclusion:
        defaults["inclusion_mode"] = doc.inclusion_mode
    document, created = document_model.objects.update_or_create(
        organization=organization,
        product=product,
        code=doc.code,
        defaults=defaults,
    )
    latest = _latest_published(version_model, document)
    if latest and latest.content == doc.content:
        return ImportReport(created=int(created))
    version = version_model.objects.create(
        document=document,
        version=_next_version(version_model, document),
        content=doc.content,
        created_by=author,
    )
    document_service.publish_version(version=version)
    if after_publish is not None:
        after_publish(version)
    return ImportReport(created=int(created), updated=1)
