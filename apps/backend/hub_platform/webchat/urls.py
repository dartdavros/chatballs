from django.urls import path

from hub_platform.webchat import views

urlpatterns = [
    path("config/", views.WebchatConfigView.as_view(), name="webchat-config"),
    path("session/", views.WebchatSessionView.as_view(), name="webchat-session"),
    path("messages/", views.WebchatMessagesView.as_view(), name="webchat-messages"),
    path("messages/<int:message_id>/audio/", views.WebchatMessageAudioView.as_view(), name="webchat-message-audio"),
    path("contact/", views.WebchatContactView.as_view(), name="webchat-contact"),
    path("call/open/", views.WebchatCallOpenView.as_view(), name="webchat-call-open"),
    path("call/decline/", views.WebchatCallDeclineView.as_view(), name="webchat-call-decline"),
]
