from channels.auth import AuthMiddlewareStack
from django.urls import path

from chatballs.conversations.consumers import ConversationEventsConsumer

# Оповещения о диалогах аутентифицируются сессией того же SPA — отдельного
# токена, как у сигналинга звонков, здесь не нужно: сокет открывает тот же
# браузер. Организация стоит в адресе, как и во всём HTTP-слое.
websocket_urlpatterns = [
    path(
        "ws/organizations/<uuid:organization_public_id>/conversations/",
        AuthMiddlewareStack(ConversationEventsConsumer.as_asgi()),
    ),
]
