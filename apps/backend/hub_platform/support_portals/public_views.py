from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle

from hub_platform.identity.models import Organization
from hub_platform.subscriptions.keys import EntitlementKey
from hub_platform.subscriptions.policy import get_effective_policy
from hub_platform.support_portals.content_services import record_feedback
from hub_platform.support_portals.models import SupportPortal
from hub_platform.support_portals.selectors import category_article_counts, public_articles
from hub_platform.support_portals.serializers import (
    category_payload,
    public_article_payload,
    public_portal_payload,
)
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.ingress import support_portal_route


class PublicPortalView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def resolve(self, request: Request):
        hostname = request.get_host().partition(":")[0].strip().lower().rstrip(".")
        route = support_portal_route(hostname)
        if route is None:
            return None
        try:
            organization = Organization.objects.get(id=route.organization_id)
        except Organization.DoesNotExist:
            return None
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            try:
                policy = get_effective_policy(context)
            except Exception:
                return None
            if not policy.has_entitlement(EntitlementKey.SUPPORT_DEPARTMENT):
                return None
            portal = (
                SupportPortal.objects.select_related(
                    "widget",
                    "widget__integration",
                    "widget__integration__channel",
                ).prefetch_related(
                    "categories",
                    "product_links__product",
                    "product_links__support_channel",
                    "product_links__support_widget",
                    "product_links__support_widget__integration",
                    "product_links__support_widget__integration__channel",
                )
                .filter(
                    id=route.resource_id,
                    organization=organization,
                    department__code="support",
                    status="PUBLISHED",
                )
                .first()
            )
            if portal is None:
                return None
            return context, portal


class PublicPortalDetailView(PublicPortalView):
    def get(self, request: Request) -> Response:
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": "Портал не найден"}, status=404)
        context, portal = resolved
        with tenant_atomic(context):
            counts = category_article_counts(portal, published_only=True)
            return Response(
                {
                    "portal": public_portal_payload(portal),
                    "categories": [
                        category_payload(
                            category, article_count=counts.get(category.id, 0)
                        )
                        for category in portal.categories.all()
                    ],
                }
            )


class PublicArticleListView(PublicPortalView):
    def get(self, request: Request) -> Response:
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": "Портал не найден"}, status=404)
        context, portal = resolved
        locale = str(request.query_params.get("locale", portal.default_locale))
        with tenant_atomic(context):
            articles = public_articles(
                portal,
                locale=locale,
                category=str(request.query_params.get("category", "")),
                query=str(request.query_params.get("q", "")).strip(),
            )
            try:
                limit = min(max(int(request.query_params.get("limit", 50)), 1), 100)
                offset = max(int(request.query_params.get("offset", 0)), 0)
            except (TypeError, ValueError):
                return Response({"detail": "Некорректная пагинация"}, status=400)
            total = articles.count()
            page = articles[offset : offset + limit]
            return Response(
                {
                    "items": [
                        public_article_payload(article, content=False)
                        for article in page
                    ],
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "total": total,
                        "hasMore": offset + limit < total,
                    },
                }
            )


class PublicArticleDetailView(PublicPortalView):
    def get(self, request: Request, article_slug: str) -> Response:
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": "Портал не найден"}, status=404)
        context, portal = resolved
        locale = str(request.query_params.get("locale", portal.default_locale))
        with tenant_atomic(context):
            article = public_articles(portal, locale=locale).filter(
                slug=article_slug
            ).first()
            if article is None:
                return Response({"detail": "Статья не найдена"}, status=404)
            return Response({"article": public_article_payload(article)})


class PublicArticleFeedbackView(PublicPortalView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "help_feedback"

    def post(self, request: Request, article_slug: str) -> Response:
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": "Портал не найден"}, status=404)
        helpful = request.data.get("helpful")
        if not isinstance(helpful, bool):
            return Response({"detail": "helpful должен быть boolean"}, status=400)
        context, portal = resolved
        locale = str(request.query_params.get("locale", portal.default_locale))
        with tenant_atomic(context):
            article = public_articles(portal, locale=locale).filter(
                slug=article_slug
            ).first()
            if article is None:
                return Response({"detail": "Статья не найдена"}, status=404)
            record_feedback(article, helpful)
            return Response({"ok": True}, status=201)
