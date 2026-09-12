from rest_framework.request import Request
from rest_framework.response import Response

from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.support_portals.article_import import import_articles
from chatballs.support_portals.portal_views import PortalBaseView


class ArticleImportView(PortalBaseView):
    def post(self, request: Request, portal_id: int) -> Response:
        portal = self.portal(request, portal_id)
        if portal is None:
            return Response({"detail": t("portals.not_found")}, status=404)
        articles = request.data.get("articles")
        if not isinstance(articles, list) or not articles:
            return Response({"detail": t("portals.articles_non_empty")}, status=400)
        result = import_articles(
            context=request.tenant_context,
            portal=portal,
            documents=articles,
        )
        payload = result.payload()
        record_audit_event(
            action="support_portal.articles_imported",
            actor=request.user,
            organization=request.tenant_context.organization,
            object_type="PortalArticle",
            object_id="",
            payload=payload,
            request=request,
        )
        return Response(payload, status=201)
