from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.support_portals import public_queries as queries
from chatballs.support_portals.feedback_limits import FEEDBACK_SCOPE
from chatballs.support_portals.models import PortalArticle, SupportPortal
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import support_portal_route
from chatballs.tenancy.lookup import load_organization


class PublicPortalView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def resolve(self, request: Request):
        hostname = request.get_host().partition(":")[0].strip().lower().rstrip(".")
        route = support_portal_route(hostname)
        if route is None:
            return None
        organization = load_organization(route.organization_id)
        if organization is None:
            return None
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            portal = (
                SupportPortal.objects.select_related(
                    "widget",
                    "widget__integration",
                    "widget__integration__channel",
                ).prefetch_related("categories")
                .filter(
                    id=route.resource_id,
                    organization=organization,
                    status="PUBLISHED",
                )
                .first()
            )
            if portal is None:
                return None
            return context, portal


class PublicPortalDetailView(PublicPortalView):
    def get(self, request):
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": t("portals.not_found")}, status=404)
        context, portal = resolved
        with tenant_atomic(context):
            return Response(queries.detail(portal))


class PublicArticleListView(PublicPortalView):
    def get(self, request):
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": t("portals.not_found")}, status=404)
        context, portal = resolved
        with tenant_atomic(context):
            try:
                return Response(queries.listing(portal, request.query_params))
            except (TypeError, ValueError):
                return Response({"detail": t("portals.invalid_pagination")}, status=400)


class PublicArticleDetailView(PublicPortalView):
    def get(self, request, article_slug):
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": t("portals.not_found")}, status=404)
        context, portal = resolved
        locale = str(request.query_params.get("locale", portal.default_locale))
        with tenant_atomic(context):
            try:
                return Response(queries.article_detail(portal, article_slug, locale))
            except PortalArticle.DoesNotExist:
                return Response({"detail": t("portals.article_not_found")}, status=404)


class PublicArticleFeedbackView(PublicPortalView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = FEEDBACK_SCOPE

    def post(self, request, article_slug):
        resolved = self.resolve(request)
        if resolved is None:
            return Response({"detail": t("portals.not_found")}, status=404)
        helpful = request.data.get("helpful")
        if not isinstance(helpful, bool):
            return Response({"detail": t("portals.helpful_must_be_boolean")}, status=400)
        context, portal = resolved
        locale = str(request.query_params.get("locale", portal.default_locale))
        with tenant_atomic(context):
            try:
                return Response(queries.feedback(portal, article_slug, locale, helpful), status=201)
            except PortalArticle.DoesNotExist:
                return Response({"detail": t("portals.article_not_found")}, status=404)
