from django.urls import path

from hub_platform.channels import views

urlpatterns = [
    path("", views.ChannelListView.as_view(), name="channel-list"),
    path("<int:channel_id>/", views.ChannelDetailView.as_view(), name="channel-detail"),
    path(
        "<int:channel_id>/connections/",
        views.ChannelConnectionsView.as_view(),
        name="channel-connections",
    ),
    path(
        "<int:channel_id>/connections/<int:integration_id>/",
        views.ChannelConnectionDetailView.as_view(),
        name="channel-connection-detail",
    ),
    path(
        "<int:channel_id>/counters/",
        views.ChannelCountersView.as_view(),
        name="channel-counters",
    ),
    path("<int:channel_id>/test-chat/", views.ChannelTestChatView.as_view(), name="channel-test-chat"),
]
