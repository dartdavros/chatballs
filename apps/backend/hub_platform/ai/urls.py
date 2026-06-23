from django.urls import path

from hub_platform.ai import doc_views as docs
from hub_platform.ai import release_views as releases
from hub_platform.ai import views


def _document_routes(prefix: str, view_set) -> list:
    return [
        path(f"{prefix}/", view_set["list_create"].as_view(), name=f"ai-{prefix}-list"),
        path(f"{prefix}/<int:document_id>/", view_set["detail"].as_view(), name=f"ai-{prefix}-detail"),
        path(f"{prefix}/<int:document_id>/versions/", view_set["add_version"].as_view(), name=f"ai-{prefix}-add-version"),
        path(
            f"{prefix}/<int:document_id>/versions/<int:version>/publish/",
            view_set["publish"].as_view(),
            name=f"ai-{prefix}-publish",
        ),
        path(f"{prefix}/<int:document_id>/rollback/", view_set["rollback"].as_view(), name=f"ai-{prefix}-rollback"),
        path(f"{prefix}/<int:document_id>/enable/", view_set["enable"].as_view(), name=f"ai-{prefix}-enable"),
        path(f"{prefix}/<int:document_id>/disable/", view_set["disable"].as_view(), name=f"ai-{prefix}-disable"),
    ]


urlpatterns = [
    path("agents/", views.AIAgentListView.as_view(), name="ai-agent-list"),
    path("agents/<int:agent_id>/", views.AIAgentDetailView.as_view(), name="ai-agent-detail"),
    path("agents/<int:agent_id>/update/", views.AIAgentUpdateView.as_view(), name="ai-agent-update"),
    path("agents/<int:agent_id>/activate/", views.AIAgentActivateView.as_view(), name="ai-agent-activate"),
    path("agents/<int:agent_id>/deactivate/", views.AIAgentDeactivateView.as_view(), name="ai-agent-deactivate"),
    path("releases/", releases.ReleaseListCreateView.as_view(), name="ai-release-list"),
    path("releases/<int:release_id>/", releases.ReleaseDetailView.as_view(), name="ai-release-detail"),
    path("releases/<int:release_id>/publish/", releases.ReleasePublishView.as_view(), name="ai-release-publish"),
    path("releases/<int:release_id>/rollback/", releases.ReleaseRollbackView.as_view(), name="ai-release-rollback"),
]

urlpatterns += _document_routes(
    "knowledge",
    {
        "list_create": docs.KnowledgeListCreateView,
        "detail": docs.KnowledgeDetailView,
        "add_version": docs.KnowledgeAddVersionView,
        "publish": docs.KnowledgePublishVersionView,
        "rollback": docs.KnowledgeRollbackView,
        "enable": docs.KnowledgeEnableView,
        "disable": docs.KnowledgeDisableView,
    },
)

urlpatterns += _document_routes(
    "prompts",
    {
        "list_create": docs.PromptListCreateView,
        "detail": docs.PromptDetailView,
        "add_version": docs.PromptAddVersionView,
        "publish": docs.PromptPublishVersionView,
        "rollback": docs.PromptRollbackView,
        "enable": docs.PromptEnableView,
        "disable": docs.PromptDisableView,
    },
)
