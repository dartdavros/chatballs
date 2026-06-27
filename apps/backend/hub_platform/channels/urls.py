from django.urls import path

from hub_platform.channels import views

urlpatterns = [
    path("", views.ChannelListView.as_view(), name="channel-list"),
    path("<int:channel_id>/test-chat/", views.ChannelTestChatView.as_view(), name="channel-test-chat"),
]
