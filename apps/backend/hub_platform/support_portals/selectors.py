from django.db.models import Count, Q, QuerySet

from hub_platform.support_portals.models import PortalArticle, SupportPortal
from hub_platform.tenancy.context import TenantContext


def portals_for_context(context: TenantContext) -> QuerySet[SupportPortal]:
    return (
        SupportPortal.objects.filter(
            organization=context.organization,
            department__code="support",
        )
        .select_related(
            "department",
            "widget_channel",
            "widget",
            "widget__integration",
            "widget__integration__channel",
        )
        .prefetch_related(
            "product_links__product",
            "product_links__support_channel",
            "product_links__support_widget",
            "product_links__support_widget__integration",
            "product_links__support_widget__integration__channel",
        )
    )


def portal_for_context(context: TenantContext, portal_id: int) -> SupportPortal:
    return portals_for_context(context).get(id=portal_id)


def public_articles(
    portal: SupportPortal,
    *,
    locale: str,
    category: str = "",
    query: str = "",
) -> QuerySet[PortalArticle]:
    articles = (
        PortalArticle.objects.filter(
            portal=portal,
            status="PUBLISHED",
            locale=locale,
            published_revision__isnull=False,
        )
        .select_related("category", "published_revision")
        .order_by("category__sort_order", "published_revision__title")
    )
    if category:
        root = portal.categories.filter(slug=category).first()
        if root is None:
            return articles.none()
        category_ids = descendant_category_ids(portal, root.id)
        articles = articles.filter(category_id__in=category_ids)
    if query:
        articles = articles.filter(
            Q(published_revision__title__icontains=query)
            | Q(published_revision__summary__icontains=query)
            | Q(published_revision__content__icontains=query)
        )
    return articles


def descendant_category_ids(portal: SupportPortal, root_id: int) -> set[int]:
    children: dict[int | None, list[int]] = {}
    for category_id, parent_id in portal.categories.values_list("id", "parent_id"):
        children.setdefault(parent_id, []).append(category_id)
    result: set[int] = set()
    pending = [root_id]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        result.add(current)
        pending.extend(children.get(current, []))
    return result


def category_article_counts(
    portal: SupportPortal, *, published_only: bool = False
) -> dict[int, int]:
    categories = list(portal.categories.all())
    direct_query = PortalArticle.objects.filter(portal=portal)
    if published_only:
        direct_query = direct_query.filter(
            status="PUBLISHED", published_revision__isnull=False
        )
    direct = dict(
        direct_query.values("category_id")
        .annotate(total=Count("id"))
        .values_list("category_id", "total")
    )
    children: dict[int | None, list[int]] = {}
    for category in categories:
        children.setdefault(category.parent_id, []).append(category.id)
    totals: dict[int, int] = {}

    def total(category_id: int) -> int:
        if category_id in totals:
            return totals[category_id]
        value = direct.get(category_id, 0)
        value += sum(total(child_id) for child_id in children.get(category_id, []))
        totals[category_id] = value
        return value

    for category in categories:
        total(category.id)
    return totals
