from django.urls import path

from chatballs.ai.external_agents import config_views as views

urlpatterns = [
    path("", views.FeatureView.as_view()),
    path("templates/<uuid:template_id>/preview/", views.TemplatePreviewView.as_view()),
    path("connections/", views.ConnectionListView.as_view()),
    path("connections/<int:connection_id>/", views.ConnectionView.as_view()),
    path("connections/<int:connection_id>/configuration/", views.ConfigurationView.as_view()),
    path("connections/<int:connection_id>/check/", views.CheckView.as_view()),
    path("connections/<int:connection_id>/key/", views.KeyView.as_view()),
    path("connections/<int:connection_id>/bindings/<int:agent_id>/", views.BindingView.as_view()),
]
