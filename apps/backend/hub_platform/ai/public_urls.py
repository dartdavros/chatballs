from django.urls import path

from hub_platform.ai.attachment_views import AttachmentDownloadView

urlpatterns = [
    path("files/<uuid:public_id>/", AttachmentDownloadView.as_view(), name="ai-attachment-download"),
]
