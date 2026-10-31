from django.urls import path

from chatballs.integrations.execution.views import RunControlView, RunDetailView, RunListView
from chatballs.integrations.execution.retention_views import RunRetentionView
from chatballs.integrations.execution.launch_views import ManualActionsView
from chatballs.integrations.execution.metadata_views import ManualLookupView

urlpatterns = [
    path("run-actions/", ManualActionsView.as_view(), name="scenario-manual-actions"),
    path("run-actions/lookup/", ManualLookupView.as_view(), name="scenario-manual-lookup"),
    path("runs/", RunListView.as_view(), name="scenario-run-list"),
    path("runs/retention/", RunRetentionView.as_view(), name="scenario-run-retention"),
    path("runs/<uuid:public_id>/", RunDetailView.as_view(), name="scenario-run-detail"),
    path("runs/<uuid:public_id>/<str:action>/", RunControlView.as_view(), name="scenario-run-control"),
]
