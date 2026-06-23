from django.urls import path

from hub_platform.ai import views

urlpatterns = [
    path("agents/", views.AIAgentListView.as_view(), name="ai-agent-list"),
    path("agents/<int:agent_id>/", views.AIAgentDetailView.as_view(), name="ai-agent-detail"),
    path("agents/<int:agent_id>/update/", views.AIAgentUpdateView.as_view(), name="ai-agent-update"),
    path("agents/<int:agent_id>/activate/", views.AIAgentActivateView.as_view(), name="ai-agent-activate"),
    path("agents/<int:agent_id>/deactivate/", views.AIAgentDeactivateView.as_view(), name="ai-agent-deactivate"),
]
