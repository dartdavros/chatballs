from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.i18n import t
from chatballs.support_portals.content_services import (
    add_revision,
    create_article,
    ensure_portal_editable,
    update_article,
)
from chatballs.support_portals.models import PortalCategory
from chatballs.tenancy.context import TenantContext


@dataclass(slots=True)
class ArticleImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: list[dict[str, str]] = field(default_factory=list)

    def payload(self) -> dict[str, object]:
        return {
            "created": self.created,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "failed": self.failed,
        }


def _required(document: dict[str, object], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError({key: t("ai.field_required", field=key)})
    return value.strip()


def _content(document: dict[str, object]) -> str:
    value = document.get("content")
    if not isinstance(value, str):
        raise ValidationError({"content": t("ai.content_required")})
    return value


def _locale(document: dict[str, object], *, default: str) -> str:
    if "locale" not in document or document["locale"] in (None, ""):
        return default
    value = document["locale"]
    if not isinstance(value, str):
        raise ValidationError({"locale": t("portals.locale_string")})
    return value.strip().lower()


def _summary(document: dict[str, object], *, default: str) -> str:
    if "summary" not in document or document["summary"] is None:
        return default
    value = document["summary"]
    if not isinstance(value, str):
        raise ValidationError({"summary": t("portals.summary_string")})
    return value.strip()


def _category_for_path(*, portal, raw_path: object) -> PortalCategory:
    if not isinstance(raw_path, list) or not raw_path:
        raise ValidationError({"categoryPath": t("ai.category_path_required")})
    parent_id = None
    category = None
    for raw_name in raw_path:
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValidationError({"categoryPath": t("ai.category_names_strings")})
        name = raw_name.strip()
        try:
            category = portal.categories.get(parent_id=parent_id, name=name)
        except (
            PortalCategory.DoesNotExist,
            PortalCategory.MultipleObjectsReturned,
        ) as error:
            raise ValidationError({"categoryPath": t("ai.category_path_not_found")}) from error
        parent_id = category.id
    assert category is not None
    return category


def _validation_detail(error: ValidationError) -> str:
    if hasattr(error, "message_dict"):
        return "; ".join(
            message for messages in error.message_dict.values() for message in messages
        )
    return "; ".join(error.messages)


@transaction.atomic
def _import_document(
    *, context: TenantContext, portal, document: dict[str, object]
) -> str:
    ensure_portal_editable(portal)
    slug = _required(document, "slug").lower()
    title = _required(document, "title")
    content = _content(document)
    summary = _summary(document, default="")
    locale = _locale(document, default=portal.default_locale)
    category = _category_for_path(portal=portal, raw_path=document.get("categoryPath"))

    existing = portal.articles.filter(locale=locale, slug=slug).first()
    if existing is None:
        create_article(
            context=context,
            portal=portal,
            data={
                "categoryId": category.id,
                "slug": slug,
                "locale": locale,
                "title": title,
                "summary": summary,
                "content": content,
            },
        )
        return "created"

    latest = existing.revisions.order_by("-revision").first()
    same_category = existing.category_id == category.id
    same_content = (
        latest is not None
        and latest.title == title
        and latest.summary == summary
        and latest.content == content
    )
    if same_content and same_category:
        return "unchanged"
    if not same_category:
        update_article(
            article=existing,
            data={
                "categoryId": category.id,
                "slug": existing.slug,
                "locale": existing.locale,
            },
        )
    if not same_content:
        add_revision(
            context=context,
            article=existing,
            data={"title": title, "summary": summary, "content": content},
        )
    return "updated"


def import_articles(
    *, context: TenantContext, portal, documents: list[object]
) -> ArticleImportResult:
    result = ArticleImportResult()
    for raw_document in documents:
        slug = ""
        if isinstance(raw_document, dict):
            raw_slug = raw_document.get("slug")
            slug = raw_slug.strip() if isinstance(raw_slug, str) else ""
        try:
            if not isinstance(raw_document, dict):
                raise ValidationError({"article": t("portals.article_object_required")})
            outcome = _import_document(
                context=context, portal=portal, document=raw_document
            )
        except ValidationError as error:
            result.failed.append({"slug": slug, "detail": _validation_detail(error)})
            continue
        if outcome == "created":
            result.created += 1
        elif outcome == "updated":
            result.updated += 1
        else:
            result.unchanged += 1
    return result
