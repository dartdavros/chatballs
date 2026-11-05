from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.api.permissions import HasCapability
from chatballs.i18n import t
from chatballs.integrations.models import Integration
from chatballs.webchat import asset_services
from chatballs.webchat.models import WidgetAsset

# Адрес иконки неизменен: каждая загрузка получает новый UUID.
_IMMUTABLE_CACHE = "public, max-age=31536000, immutable"


class WidgetAssetUploadView(APIView):
    """Загрузка иконки кнопки или шапки веб-виджета → ``{ url }``."""

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [HasCapability]
    required_capability = "integrations.manage"

    def post(self, request: Request, integration_id: int) -> Response:
        try:
            result = asset_services.upload(request.tenant_context, integration_id,
                request.FILES.get("file"), request=request)
        except Integration.DoesNotExist:
            return Response({"detail": t("settings.integration_not_found")}, status=404)
        except ValidationError as error:
            detail = error.message_dict["file"][0]
            return Response({"detail": detail, "errors": {"file": detail}}, status=400)
        return Response(result, status=201)


class WidgetAssetView(APIView):
    """Иконка виджета по публичной ссылке.

    Её показывает лоадер на чужом сайте, где нет сессии: защита —
    непредсказуемый UUID и резолв организации через ingress-каталог.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request: Request, public_id) -> FileResponse:
        try:
            opened_file, _name, content_type = asset_services.open_asset(public_id)
        except WidgetAsset.DoesNotExist:
            raise Http404 from None
        response = FileResponse(opened_file, content_type=content_type)
        # SVG очищен при загрузке; заголовки — второй рубеж на случай, если
        # адрес откроют как документ: ничего не исполнять, никуда не ходить,
        # тип не угадывать. Картинку можно встраивать на любой сайт.
        response["Content-Security-Policy"] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        response["X-Content-Type-Options"] = "nosniff"
        response["Cross-Origin-Resource-Policy"] = "cross-origin"
        response["Cache-Control"] = _IMMUTABLE_CACHE
        return response
