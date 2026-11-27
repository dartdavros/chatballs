from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from chatballs.i18n import t
from chatballs.support_portals.models import PortalCategory, SupportPortal
from chatballs.support_portals.statuses import PortalStatus
from chatballs.tenancy.context import TenantContext


def create_category(
    *, context: TenantContext, portal: SupportPortal, data: dict
) -> PortalCategory:
    ensure_portal_editable(portal)
    parent = category_for_portal(portal, data.get("parentId")) if data.get("parentId") else None
    require_editable_category(parent)
    name = str(data.get("name", "")).strip()
    category = PortalCategory(
        organization=context.organization,
        portal=portal,
        parent=parent,
        slug=str(data.get("slug", "")).strip().lower() or _category_slug(portal, name),
        name=name,
        description=str(data.get("description", "")).strip(),
        sort_order=int(data.get("sortOrder", 0)),
    )
    category.full_clean()
    category.save()
    return category


def _category_slug(portal: SupportPortal, name: str) -> str:
    base = slugify(name)[:54] or "category"
    slug = base
    suffix = 2
    while portal.categories.filter(slug=slug).exists():
        slug = f"{base[: 63 - len(str(suffix)) - 1]}-{suffix}"
        suffix += 1
    return slug


def update_category(
    *, portal: SupportPortal, category: PortalCategory, data: dict
) -> PortalCategory:
    ensure_portal_editable(portal)
    require_editable_category(category)
    category.parent = (
        category_for_portal(portal, data.get("parentId")) if data.get("parentId") else None
    )
    require_editable_category(category.parent)
    category.slug = str(data.get("slug", category.slug)).strip().lower()
    category.name = str(data.get("name", category.name)).strip()
    category.description = str(
        data.get("description", category.description)
    ).strip()
    category.sort_order = int(data.get("sortOrder", category.sort_order))
    category.full_clean()
    category.save()
    return category


def delete_category(*, portal: SupportPortal, category: PortalCategory) -> None:
    ensure_portal_editable(portal)
    require_editable_category(category)
    if category.children.exists():
        raise ValidationError(
            {"category": t("portals.move_nested_sections_first")}
        )
    if category.articles.exists():
        raise ValidationError(
            {"category": t("portals.move_articles_first")}
        )
    category.delete()


def category_for_portal(portal: SupportPortal, category_id) -> PortalCategory:
    if isinstance(category_id, bool):
        raise ValidationError({"categoryId": t("portals.section_not_found")})
    try:
        return portal.categories.get(id=int(category_id))
    except (PortalCategory.DoesNotExist, TypeError, ValueError) as error:
        raise ValidationError({"categoryId": t("portals.section_not_found")}) from error


def ensure_portal_editable(portal: SupportPortal) -> None:
    if portal.status == PortalStatus.ARCHIVED:
        raise ValidationError(
            {"portal": t("portals.restore_to_edit_content")}
        )


def require_editable_category(category: PortalCategory | None) -> None:
    if category is not None and category.is_system:
        raise ValidationError({"category": t("portals.system_section_readonly")})


@transaction.atomic
def article_category(portal: SupportPortal, category_id) -> PortalCategory:
    if category_id is not None:
        return category_for_portal(portal, category_id)
    SupportPortal.objects.select_for_update().get(pk=portal.pk)
    category, _ = portal.categories.get_or_create(
        is_system=True,
        defaults={
            "organization_id": portal.organization_id,
            "slug": _category_slug(portal, "uncategorized"),
            "name": t("portals.uncategorized", language=portal.default_locale),
        },
    )
    return category
