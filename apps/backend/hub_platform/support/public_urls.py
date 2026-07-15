from django.urls import path

from hub_platform.support import public_views

urlpatterns = [
    path(
        "sessions/",
        public_views.SupportSessionStartView.as_view(),
        name="support-session-start",
    ),
    path(
        "sessions/messages/",
        public_views.SupportSessionMessagesView.as_view(),
        name="support-session-messages",
    ),
]
