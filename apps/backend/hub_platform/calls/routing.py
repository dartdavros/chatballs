from django.urls import path

from hub_platform.calls.consumers import CallSignalingConsumer

websocket_urlpatterns = [
    path("ws/calls/", CallSignalingConsumer.as_asgi()),
]
