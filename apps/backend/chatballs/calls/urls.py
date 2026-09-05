from django.urls import path

from chatballs.calls import views

urlpatterns = [
    path(
        "conversations/<int:conversation_id>/",
        views.CallCreateView.as_view(),
        name="call-create",
    ),
    path(
        "conversations/<int:conversation_id>/active/",
        views.ConversationActiveCallView.as_view(),
        name="call-conversation-active",
    ),
    path("<uuid:call_session_id>/", views.CallDetailView.as_view(), name="call-detail"),
    path(
        "<uuid:call_session_id>/cancel/",
        views.CallCancelView.as_view(),
        name="call-cancel",
    ),
    path(
        "<uuid:call_session_id>/access-token/",
        views.StaffAccessTokenView.as_view(),
        name="call-staff-access-token",
    ),
]
