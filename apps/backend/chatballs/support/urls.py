from django.urls import include, path

from chatballs.support import views

urlpatterns = [
    path("portals/", include("chatballs.support_portals.urls")),
    path("contracts/", views.SupportContractListView.as_view(), name="support-contract-list"),
    path(
        "contracts/<int:contract_id>/",
        views.SupportContractDetailView.as_view(),
        name="support-contract-detail",
    ),
    path(
        "contracts/<int:contract_id>/status/",
        views.SupportContractStatusView.as_view(),
        name="support-contract-status",
    ),
    path(
        "snapshots/",
        views.SupportSnapshotsBySubjectView.as_view(),
        name="support-snapshots-by-subject",
    ),
]
