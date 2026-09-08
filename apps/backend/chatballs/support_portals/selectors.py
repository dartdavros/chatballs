from django.db.models import (
    Case,
    Count,
    IntegerField,
    OuterRef,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)

from chatballs.support_portals.models import (
    PortalArticle,
    PortalArticleRevision,
    PortalCategory,
    SupportPortal,
)
from chatballs.support_portals.statuses import PortalStatus
from chatballs.tenancy.context import TenantContext


def portals_for_context(context: TenantContext) -> QuerySet[SupportPortal]:
    return (
        SupportPortal.objects.filter(
            organization=context.organization,
        )
        .select_related(
            "widget_channel",
            "widget",
            "widget__integration",
            "widget__integration__channel",
        )
    )


def portal_for_context(context: TenantContext, portal_id: int) -> SupportPortal:
    return portals_for_context(context).get(id=portal_id)


def portals_page_queryset(context: TenantContext, params) -> QuerySet[SupportPortal]:
    """Список порталов (кадр PT1): статус и поиск — параметры запроса.

    Архивные всегда идут последними: страница отдаёт тот же порядок, который
    раньше выстраивал браузер по полному списку.
    """
    portals = portals_for_context(context)
    statuses = [value for value in params.getlist("status") if value]
    if statuses:
        portals = portals.filter(status__in=statuses)
    query = params.get("q", "").strip()
    if query:
        portals = portals.filter(
            Q(name__icontains=query)
            | Q(hosted_domain__icontains=query)
            | Q(custom_domain__icontains=query)
        )
    return portals.annotate(
        _archived=Case(
            When(status=PortalStatus.ARCHIVED, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by("_archived", "name", "id")


def portal_articles_queryset(portal: SupportPortal, params) -> QuerySet[PortalArticle]:
    """Библиотека статей портала (кадр PT3): категория, язык, статус и поиск.

    Поиск идёт по последней редакции — заголовку и краткому описанию, — как и
    в редакторе: сравнивать со старыми версиями было бы неожиданно.
    """
    latest = PortalArticleRevision.objects.filter(article_id=OuterRef("pk")).order_by("-revision")
    articles = (
        PortalArticle.objects.filter(portal=portal)
        .select_related("category", "published_revision")
        .prefetch_related("revisions", "files", "feedback")
        .annotate(
            latest_title=Subquery(latest.values("title")[:1]),
            latest_summary=Subquery(latest.values("summary")[:1]),
        )
    )
    category = params.get("category")
    if category and str(category).isdigit():
        # Фильтр охватывает поддерево категории — тем же обходом, что и публичный портал.
        articles = articles.filter(
            category_id__in=descendant_category_ids(portal, int(category))
        )
    locales = [value for value in params.getlist("locale") if value]
    if locales:
        articles = articles.filter(locale__in=locales)
    statuses = [value for value in params.getlist("status") if value]
    if statuses:
        articles = articles.filter(status__in=statuses)
    query = params.get("q", "").strip()
    if query:
        articles = articles.filter(
            Q(slug__icontains=query)
            | Q(latest_title__icontains=query)
            | Q(latest_summary__icontains=query)
        )
    return articles.order_by("-id")


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
        .prefetch_related("files")
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


def portal_content_counts(context: TenantContext) -> dict[int, dict[str, int]]:
    """Разделы и статьи по порталам — колонка «Материалы» списка (кадр PT1)."""

    counts: dict[int, dict[str, int]] = {}
    categories = (
        PortalCategory.objects.filter(organization=context.organization)
        .values("portal_id")
        .annotate(total=Count("id"))
    )
    for row in categories:
        counts.setdefault(row["portal_id"], {})["categories"] = row["total"]
    articles = (
        PortalArticle.objects.filter(organization=context.organization)
        .values("portal_id")
        .annotate(total=Count("id"))
    )
    for row in articles:
        counts.setdefault(row["portal_id"], {})["articles"] = row["total"]
    return counts
