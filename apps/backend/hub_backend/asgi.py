import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hub_backend.settings")

# HTTP-приложение инициализируется до импорта consumer'ов (django.setup).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from hub_platform.calls.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        # Собственный signaling звонков (SPEC-HUB-0013 §9). Аутентификация —
        # первым сообщением по call access token, Django-сессия не нужна.
        "websocket": URLRouter(websocket_urlpatterns),
    }
)
