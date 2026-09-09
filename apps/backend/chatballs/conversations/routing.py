from channels.auth import AuthMiddlewareStack
from django.urls import path

from chatballs.conversations.consumers import ConversationEventsConsumer
from chatballs.http.ws_middleware import websocket_boundary

# Оповещения о диалогах аутентифицируются сессией того же SPA — отдельного
# токена, как у сигналинга звонков, здесь не нужно: сокет открывает тот же
# браузер. Организация стоит в адресе, как и во всём HTTP-слое.
#
# websocket_boundary снаружи AuthMiddlewareStack: он приводит имена cookie к
# тем, по которым Channels ищет сессию (по TLS браузер держит __Host-…), и
# отбивает хендшейк с чужим Origin.
websocket_urlpatterns = [
    path(
        "ws/organizations/<uuid:organization_public_id>/conversations/",
        websocket_boundary(AuthMiddlewareStack(ConversationEventsConsumer.as_asgi())),
    ),
]
