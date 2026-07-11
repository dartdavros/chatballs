from django.urls import path

from hub_platform.calls import views

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
    path("invites/resolve/", views.InviteResolveView.as_view(), name="call-invite-resolve"),
    path("access/state/", views.CallAccessStateView.as_view(), name="call-access-state"),
    path("access/accept/", views.CallAccessAcceptView.as_view(), name="call-access-accept"),
    path("access/decline/", views.CallAccessDeclineView.as_view(), name="call-access-decline"),
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
