from django.urls import path

from chatballs.calls.consumers import CallSignalingConsumer

websocket_urlpatterns = [
    path("ws/calls/", CallSignalingConsumer.as_asgi()),
]
