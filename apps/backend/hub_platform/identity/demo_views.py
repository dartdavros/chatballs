"""Демо-данные организации: статус, установка, удаление («Настройки»)."""

import mimetypes

from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.api.permissions import HasCapability
from hub_platform.identity.demo_seed import manifest, service


def _error(error: ValidationError, status: int) -> Response:
    if hasattr(error, "message_dict"):
        detail = "; ".join(
            message for messages in error.message_dict.values() for message in messages
        )
    else:
        detail = "; ".join(error.messages)
    return Response({"detail": detail}, status=status)


class DemoDataView(APIView):
    permission_classes = [HasCapability]
    required_capabilities = {
        "GET": "settings.view",
        "POST": "company.manage",
        "DELETE": "company.manage",
    }
    require_organization_scope = True

    def get(self, request: Request) -> Response:
        return Response(service.demo_status(request.tenant_context.organization))

    def post(self, request: Request) -> Response:
        try:
            service.request_install(context=request.tenant_context, actor=request.user)
        except service.DemoBusy as error:
            return _error(error, 409)
        except ValidationError as error:
            return _error(error, 400)
        return Response(service.demo_status(request.tenant_context.organization), status=202)

    def delete(self, request: Request) -> Response:
        try:
            service.request_remove(context=request.tenant_context, actor=request.user)
        except service.DemoBusy as error:
            return _error(error, 409)
        except ValidationError as error:
            return _error(error, 400)
        return Response(service.demo_status(request.tenant_context.organization), status=202)


class DemoMediaView(APIView):
    """Публичные медиа демо-набора (аватары контактов) из пакета бэкенда.

    Отдаёт только файлы каталога demo_seed/data/media/avatars; путь
    нормализуется, выход за каталог невозможен.
    """

    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request, name: str):
        root = (manifest.MEDIA_DIR / "avatars").resolve()
        candidate = (root / name).resolve()
        if root not in candidate.parents or not candidate.is_file():
            raise Http404("Demo media not found")
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        response = FileResponse(candidate.open("rb"), content_type=content_type)
        response["Cache-Control"] = "public, max-age=86400"
        return response
