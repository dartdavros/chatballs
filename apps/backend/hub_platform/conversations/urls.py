from django.urls import path

from hub_platform.conversations import views

urlpatterns = [
    path("", views.ConversationListView.as_view(), name="conversation-list"),
    path("stats/", views.ConversationStatsView.as_view(), name="conversation-stats"),
    path("command-overview/", views.CommandOverviewView.as_view(), name="conversation-command-overview"),
    path("clients/", views.ClientsView.as_view(), name="conversation-clients"),
    path("clients/<int:contact_id>/", views.ClientDetailView.as_view(), name="conversation-client-detail"),
    path("<int:conversation_id>/", views.ConversationDetailView.as_view(), name="conversation-detail"),
    path("<int:conversation_id>/claim/", views.ConversationClaimView.as_view(), name="conversation-claim"),
    path("<int:conversation_id>/release/", views.ConversationReleaseView.as_view(), name="conversation-release"),
    path("<int:conversation_id>/return-queue/", views.ConversationReturnQueueView.as_view(), name="conversation-return-queue"),
    path("<int:conversation_id>/messages/", views.ConversationMessageView.as_view(), name="conversation-messages"),
    path("<int:conversation_id>/request-contact/", views.ConversationRequestContactView.as_view(), name="conversation-request-contact"),
    path("<int:conversation_id>/close/", views.ConversationCloseView.as_view(), name="conversation-close"),
]
