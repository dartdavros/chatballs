from django.urls import path

from chatballs.support_portals import public_views

urlpatterns = [
    path("", public_views.PublicPortalDetailView.as_view(), name="public-support-portal"),
    path("articles/", public_views.PublicArticleListView.as_view(), name="public-support-articles"),
    path("articles/<slug:article_slug>/", public_views.PublicArticleDetailView.as_view(), name="public-support-article"),
    path("articles/<slug:article_slug>/feedback/", public_views.PublicArticleFeedbackView.as_view(), name="public-support-feedback"),
]
