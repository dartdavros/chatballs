import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "chatballs_backend.settings_app")

# Django initializes before consumers import models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from chatballs.calls.routing import websocket_urlpatterns as call_routes  # noqa: E402
from chatballs.conversations.routing import (  # noqa: E402
    websocket_urlpatterns as conversation_routes,
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": URLRouter(call_routes + conversation_routes),
    }
)
