from django.urls import path

from hub_platform.conversations import reporting_views, views

urlpatterns = [
    path("", views.ConversationListView.as_view(), name="conversation-list"),
    path("stats/", reporting_views.ConversationStatsView.as_view(), name="conversation-stats"),
    path("command-overview/", reporting_views.CommandOverviewView.as_view(), name="conversation-command-overview"),
    path("clients/", reporting_views.ClientsView.as_view(), name="conversation-clients"),
    path("clients/<int:contact_id>/", reporting_views.ClientDetailView.as_view(), name="conversation-client-detail"),
    path("<int:conversation_id>/", views.ConversationDetailView.as_view(), name="conversation-detail"),
    path("<int:conversation_id>/claim/", views.ConversationClaimView.as_view(), name="conversation-claim"),
    path("<int:conversation_id>/release/", views.ConversationReleaseView.as_view(), name="conversation-release"),
    path("<int:conversation_id>/return-queue/", views.ConversationReturnQueueView.as_view(), name="conversation-return-queue"),
    path("<int:conversation_id>/messages/", views.ConversationMessageView.as_view(), name="conversation-messages"),
    path("<int:conversation_id>/request-contact/", views.ConversationRequestContactView.as_view(), name="conversation-request-contact"),
    path("<int:conversation_id>/close/", views.ConversationCloseView.as_view(), name="conversation-close"),
    path("<int:conversation_id>/spam/", views.ConversationSpamView.as_view(), name="conversation-spam"),
    path("<int:conversation_id>/group/", views.ConversationGroupView.as_view(), name="conversation-group"),
    path("<int:conversation_id>/assignee/", views.ConversationAssigneeView.as_view(), name="conversation-assignee"),
]
