from django.urls import path

from hub_platform.calls import views

urlpatterns = [
    path("invites/resolve/", views.InviteResolveView.as_view(), name="call-invite-resolve"),
    path("access/state/", views.CallAccessStateView.as_view(), name="call-access-state"),
    path("access/accept/", views.CallAccessAcceptView.as_view(), name="call-access-accept"),
    path("access/decline/", views.CallAccessDeclineView.as_view(), name="call-access-decline"),
    path("access/end/", views.CallAccessEndView.as_view(), name="call-access-end"),
]
