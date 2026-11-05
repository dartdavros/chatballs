from django.urls import path

from chatballs.integrations.scenarios import views
from chatballs.integrations.scenarios.catalog_views import ScenarioCatalogView
from chatballs.integrations.scenarios.entity_link_views import (
    EntityLinkCommandView,
    EntityLinkSearchView,
    EntityLinksView,
)
from chatballs.integrations.scenarios.key_views import ScenarioRotateKeyView
from chatballs.integrations.scenarios.synchronization_views import ServiceSynchronizationView

urlpatterns = [
    path("entity-links/", EntityLinksView.as_view(), name="entity-links"),
    path("entity-links/<int:pk>/search/", EntityLinkSearchView.as_view(), name="entity-link-search"),
    path("entity-links/<int:pk>/", EntityLinkCommandView.as_view(), name="entity-link-command"),
    path("scenarios/", views.ScenarioListView.as_view(), name="scenario-list"),
    path("scenarios/check/", views.ScenarioCheckView.as_view(), name="scenario-check"),
    path("scenarios/catalog/", ScenarioCatalogView.as_view(), name="scenario-catalog"),
    path("scenarios/<uuid:public_id>/", views.ScenarioDetailView.as_view(), name="scenario-detail"),
    path("scenarios/<uuid:public_id>/copy/", views.ScenarioCopyView.as_view(), name="scenario-copy"),
    path("scenarios/<uuid:public_id>/keys/<str:trigger_id>/rotate/", ScenarioRotateKeyView.as_view(), name="scenario-rotate-key"),
    path("services/<int:connection_id>/presets/<slug:key>/", views.ScenarioPresetView.as_view(), name="scenario-preset"),
    path("services/<int:connection_id>/synchronization/", ServiceSynchronizationView.as_view(), name="service-synchronization"),
]
