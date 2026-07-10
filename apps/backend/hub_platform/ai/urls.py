from django.urls import path

from hub_platform.ai import views

urlpatterns = [
    path("agents/", views.AIAgentListView.as_view(), name="ai-agent-list"),
    path("agents/<int:agent_id>/", views.AIAgentDetailView.as_view(), name="ai-agent-detail"),
    path("agents/<int:agent_id>/update/", views.AIAgentUpdateView.as_view(), name="ai-agent-update"),
    path("agents/<int:agent_id>/activate/", views.AIAgentActivateView.as_view(), name="ai-agent-activate"),
    path("agents/<int:agent_id>/deactivate/", views.AIAgentDeactivateView.as_view(), name="ai-agent-deactivate"),
    path("knowledge/", views.KnowledgeListCreateView.as_view(), name="ai-knowledge-list"),
    path("knowledge/import/", views.KnowledgeImportView.as_view(), name="ai-knowledge-import"),
    path("knowledge/<int:knowledge_id>/", views.KnowledgeDetailView.as_view(), name="ai-knowledge-detail"),
    path("knowledge/<int:knowledge_id>/attachments/", views.KnowledgeAttachmentUploadView.as_view(), name="ai-knowledge-attachment-upload"),
    path(
        "knowledge/<int:knowledge_id>/attachments/<int:attachment_id>/",
        views.KnowledgeAttachmentDeleteView.as_view(),
        name="ai-knowledge-attachment-delete",
    ),
    path("files/<uuid:public_id>/", views.AttachmentDownloadView.as_view(), name="ai-attachment-download"),
]
