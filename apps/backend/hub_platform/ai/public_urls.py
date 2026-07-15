from django.urls import path

from hub_platform.ai import views

urlpatterns = [
    path("files/<uuid:public_id>/", views.AttachmentDownloadView.as_view(), name="ai-attachment-download"),
]
