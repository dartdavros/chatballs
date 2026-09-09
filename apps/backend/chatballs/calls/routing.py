from django.urls import path

from chatballs.calls.consumers import CallSignalingConsumer
from chatballs.http.ws_middleware import SameOriginWebSocketMiddleware

# Сигналинг звонка аутентифицируется call access token, а не сессией, поэтому
# переименование cookie ему не нужно. Проверка Origin — нужна: страницу звонка
# открывает браузер, и чужой сайт не должен открывать сокет за него.
websocket_urlpatterns = [
    path("ws/calls/", SameOriginWebSocketMiddleware(CallSignalingConsumer.as_asgi())),
]
