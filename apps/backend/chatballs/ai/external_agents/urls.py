from django.urls import path

from chatballs.ai.external_agents.file_views import FileView, UploadView
from chatballs.ai.external_agents.operation_views import HandoffView, MessagesView
from chatballs.ai.external_agents.template_views import TemplateView
from chatballs.ai.external_agents.views import DeliveryView, HistoryView, ResultView

urlpatterns = [
    path("connections/<int:connection_id>/conversations/<int:conversation_id>/messages/", MessagesView.as_view()),
    path("connections/<int:connection_id>/conversations/<int:conversation_id>/handoff/", HandoffView.as_view()),
    path("connections/<int:connection_id>/conversations/<int:conversation_id>/files/", UploadView.as_view()),
    path("connections/<int:connection_id>/conversations/<int:conversation_id>/files/<uuid:file_id>/", FileView.as_view()),
    path("connections/<int:connection_id>/conversations/<int:conversation_id>/reply-templates/", TemplateView.as_view()),
    path("connections/<int:connection_id>/requests/<uuid:request_id>/result/", ResultView.as_view()),
    path("connections/<int:connection_id>/deliveries/<uuid:delivery_id>/", DeliveryView.as_view()),
    path("connections/<int:connection_id>/conversations/<int:conversation_id>/history/", HistoryView.as_view()),
]
