from django.urls import path

from hub_platform.support import views

urlpatterns = [
    path("sessions/", views.SupportSessionStartView.as_view(), name="support-session-start"),
    path(
        "sessions/messages/",
        views.SupportSessionMessagesView.as_view(),
        name="support-session-messages",
    ),
]
