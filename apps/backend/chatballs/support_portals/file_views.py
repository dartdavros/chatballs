from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView

from chatballs.support_portals.content_services import INLINE_CONTENT_TYPES
from chatballs.support_portals.models import PortalArticleFile
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import portal_article_file_route
from chatballs.tenancy.lookup import load_organization


class PortalArticleFileView(APIView):
    """Файл статьи портала по публичной ссылке.

    Ссылка попадает в Markdown статьи и открывается посетителем портала, у
    которого нет сессии хаба: защита — непредсказуемый UUID и резолв
    организации через ingress-директорию (как у вложений знаний).
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request, public_id) -> FileResponse:
        route = portal_article_file_route(str(public_id))
        if route is None:
            raise Http404
        organization = load_organization(route.organization_id)
        if organization is None:
            raise Http404
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            article_file = PortalArticleFile.objects.filter(
                id=route.resource_id,
                public_id=public_id,
                organization=organization,
                article__organization=organization,
            ).first()
            if article_file is None:
                raise Http404
            opened_file = article_file.file.open("rb")
            original_name = article_file.original_name
            content_type = article_file.content_type
        # Картинка встроена в статью тегом <img>, поэтому её отдаём inline. Но
        # только её: тип пришёл от загружавшего, а страница открывается на
        # домене портала — что-то вроде text/html здесь стало бы кодом на чужом
        # домене. Всё, что не картинка и не PDF, уходит вложением.
        inline = content_type in INLINE_CONTENT_TYPES
        response = FileResponse(opened_file, filename=original_name, as_attachment=not inline)
        if content_type:
            response.headers["Content-Type"] = content_type
        # Собственная политика поверх политики поверхности: файл посетителя не
        # должен ничего исполнять и никуда ходить, даже если CSP установки
        # когда-нибудь ослабят. Актуально для svg — картинки со скриптом внутри.
        response.headers["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response
