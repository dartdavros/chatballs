from django.urls import path

from chatballs.integrations.execution.agent_actions import AgentActionsView
from chatballs.integrations.execution.ai_metadata import ApprovalLookupView
from chatballs.integrations.execution.launch_views import ManualActionsView
from chatballs.integrations.execution.metadata_views import ManualLookupView
from chatballs.integrations.execution.retention_views import RunRetentionView
from chatballs.integrations.execution.views import RunControlView, RunDetailView, RunListView

urlpatterns = [
    path("agent-actions/<int:channel_id>/", AgentActionsView.as_view(), name="agent-service-actions"),
    path("run-actions/", ManualActionsView.as_view(), name="scenario-manual-actions"),
    path("run-actions/lookup/", ManualLookupView.as_view(), name="scenario-manual-lookup"),
    path("runs/", RunListView.as_view(), name="scenario-run-list"),
    path("runs/retention/", RunRetentionView.as_view(), name="scenario-run-retention"),
    path("runs/<uuid:public_id>/", RunDetailView.as_view(), name="scenario-run-detail"),
    path("runs/<uuid:public_id>/approval-lookup/", ApprovalLookupView.as_view(), name="run-approval-lookup"),
    path("runs/<uuid:public_id>/<str:action>/", RunControlView.as_view(), name="scenario-run-control"),
]
