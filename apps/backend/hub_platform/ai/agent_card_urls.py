"""Роуты единой сущности «Агент» (ADR-HUB-0041 §4)."""

from django.urls import path

from hub_platform.ai import agent_card_views as views
from hub_platform.channels.views import ChannelTestChatView

urlpatterns = [
    path("", views.AgentCardListView.as_view(), name="agent-card-list"),
    path("<int:agent_id>/", views.AgentCardDetailView.as_view(), name="agent-card-detail"),
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
    # Тестовый чат исполняет агента канала; вьюха принимает channel_id — id
    # карточки и канала совпадают по построению.
    path(
        "<int:channel_id>/test-chat/",
        ChannelTestChatView.as_view(),
        name="agent-card-test-chat",
    ),
]
