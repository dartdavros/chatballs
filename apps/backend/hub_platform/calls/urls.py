from django.urls import path

from hub_platform.calls import views

urlpatterns = [
    path(
        "conversations/<int:conversation_id>/",
        views.CallCreateView.as_view(),
        name="call-create",
    ),
    path("invites/resolve/", views.InviteResolveView.as_view(), name="call-invite-resolve"),
    path("<uuid:call_session_id>/", views.CallDetailView.as_view(), name="call-detail"),
    path(
        "<uuid:call_session_id>/access-token/",
        views.StaffAccessTokenView.as_view(),
        name="call-staff-access-token",
    ),
]
