from django.urls import path

from hub_platform.ai import agent_views, bulk_views, category_views, views

urlpatterns = [
    path("agents/", agent_views.AIAgentListView.as_view(), name="ai-agent-list"),
    path("agents/<int:agent_id>/", agent_views.AIAgentDetailView.as_view(), name="ai-agent-detail"),
    path(
        "agents/<int:agent_id>/update/",
        agent_views.AIAgentUpdateView.as_view(),
        name="ai-agent-update",
    ),
    path(
        "agents/<int:agent_id>/activate/",
        agent_views.AIAgentActivateView.as_view(),
        name="ai-agent-activate",
    ),
    path(
        "agents/<int:agent_id>/deactivate/",
        agent_views.AIAgentDeactivateView.as_view(),
        name="ai-agent-deactivate",
    ),
    path(
        "agents/<int:agent_id>/knowledge/select-category/",
        bulk_views.AgentCategoryKnowledgeSelectView.as_view(),
        name="ai-agent-knowledge-select-category",
    ),
    path("knowledge/", views.KnowledgeListCreateView.as_view(), name="ai-knowledge-list"),
    path(
        "knowledge/bulk/move/",
        bulk_views.KnowledgeBulkMoveView.as_view(),
        name="ai-knowledge-bulk-move",
    ),
    path(
        "knowledge/bulk/agent/",
        bulk_views.AgentKnowledgeLinkView.as_view(),
        name="ai-knowledge-bulk-agent",
    ),
    path(
        "portal-articles/bulk/agent/",
        bulk_views.AgentPortalArticleLinkView.as_view(),
        name="ai-portal-article-bulk-agent",
    ),
    path(
        "knowledge/categories/",
        category_views.KnowledgeCategoryListCreateView.as_view(),
        name="ai-knowledge-category-list",
    ),
    path(
        "knowledge/categories/<int:category_id>/",
        category_views.KnowledgeCategoryDetailView.as_view(),
        name="ai-knowledge-category-detail",
    ),
    path("knowledge/import/", views.KnowledgeImportView.as_view(), name="ai-knowledge-import"),
    path(
        "knowledge/<int:knowledge_id>/",
        views.KnowledgeDetailView.as_view(),
        name="ai-knowledge-detail",
    ),
    path(
        "knowledge/<int:knowledge_id>/attachments/",
        views.KnowledgeAttachmentUploadView.as_view(),
        name="ai-knowledge-attachment-upload",
    ),
    path(
        "knowledge/<int:knowledge_id>/attachments/<int:attachment_id>/",
        views.KnowledgeAttachmentDeleteView.as_view(),
        name="ai-knowledge-attachment-delete",
    ),
]
