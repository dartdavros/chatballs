from django.urls import path

from chatballs.support import public_views

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
    path(
        "sessions/messages/<int:message_id>/audio/",
        public_views.SupportSessionAudioView.as_view(),
        name="support-session-audio",
    ),
    path(
        "sessions/messages/<int:message_id>/attachment/",
        public_views.SupportSessionAttachmentView.as_view(),
        name="support-session-attachment",
    ),
]
