from django.urls import path

from hub_platform.ai import bulk_views, category_views, views

urlpatterns = [
    # agentId — id AIAgent, как и в knowledge/bulk/agent/ (CRUD агентов — /agents/).
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
