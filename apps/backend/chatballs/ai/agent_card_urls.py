"""Роуты единой сущности «Агент» (ADR-CHATBALLS-0041 §4)."""

from django.urls import path

from chatballs.ai import agent_card_views as views
from chatballs.ai.external_agents import test_views
from chatballs.ai.test_chat_views import AgentCardTestChatView

urlpatterns = [
    path("<int:channel_id>/external-test/", test_views.TestDefinitionView.as_view()),
    path("<int:channel_id>/external-test/<uuid:scope_id>/", test_views.TestSessionView.as_view()),
    path("<int:channel_id>/external-test/<uuid:scope_id>/files/<int:message_id>/", test_views.TestFileView.as_view()),
    path("", views.AgentCardListView.as_view(), name="agent-card-list"),
    path("directory/", views.AgentDirectoryView.as_view(), name="agent-directory"),
    path("<int:agent_id>/", views.AgentCardDetailView.as_view(), name="agent-card-detail"),
    path("<int:agent_id>/tools/", views.AgentCardToolsView.as_view(), name="agent-card-tools"),
    path(
        "<int:agent_id>/activate/",
        views.AgentCardActivateView.as_view(),
        name="agent-card-activate",
    ),
    path(
        "<int:agent_id>/deactivate/",
        views.AgentCardDeactivateView.as_view(),
        name="agent-card-deactivate",
    ),
    path(
        "<int:agent_id>/connections/",
        views.AgentCardConnectionsView.as_view(),
        name="agent-card-connections",
    ),
    path(
        "<int:agent_id>/connections/<int:integration_id>/",
        views.AgentCardConnectionDetailView.as_view(),
        name="agent-card-connection-detail",
    ),
    path(
        "<int:agent_id>/test-chat/",
        AgentCardTestChatView.as_view(),
        name="agent-card-test-chat",
    ),
]
