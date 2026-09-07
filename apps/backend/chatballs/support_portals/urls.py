from django.urls import path

from chatballs.support_portals import article_import_views, content_views, portal_views

urlpatterns = [
    path("", portal_views.PortalListView.as_view(), name="support-portal-list"),
    path("<int:portal_id>/", portal_views.PortalDetailView.as_view(), name="support-portal-detail"),
    path("<int:portal_id>/status/", portal_views.PortalStatusView.as_view(), name="support-portal-status"),
    path("<int:portal_id>/products/", portal_views.PortalProductsView.as_view(), name="support-portal-products"),
    path("<int:portal_id>/support-channels/", portal_views.PortalSupportChannelsView.as_view(), name="support-portal-support-channels"),
    path("<int:portal_id>/domain/", portal_views.PortalDomainView.as_view(), name="support-portal-domain"),
    path("<int:portal_id>/domain/verify/", portal_views.PortalDomainVerifyView.as_view(), name="support-portal-domain-verify"),
    path("<int:portal_id>/categories/", content_views.CategoryListView.as_view(), name="support-portal-categories"),
    path("<int:portal_id>/categories/<int:category_id>/", content_views.CategoryDetailView.as_view(), name="support-portal-category-detail"),
    path("<int:portal_id>/articles/", content_views.ArticleListView.as_view(), name="support-portal-articles"),
    path("<int:portal_id>/articles/import/", article_import_views.ArticleImportView.as_view(), name="support-portal-article-import"),
    path("<int:portal_id>/articles/<int:article_id>/", content_views.ArticleDetailView.as_view(), name="support-portal-article"),
    path("<int:portal_id>/articles/<int:article_id>/files/", content_views.ArticleFileListView.as_view(), name="support-portal-article-files"),
    path("<int:portal_id>/articles/<int:article_id>/files/<int:file_id>/", content_views.ArticleFileDetailView.as_view(), name="support-portal-article-file-detail"),
    path("<int:portal_id>/articles/<int:article_id>/revisions/", content_views.ArticleRevisionListView.as_view(), name="support-portal-article-revisions"),
    path("<int:portal_id>/articles/<int:article_id>/publish/", content_views.ArticlePublishView.as_view(), name="support-portal-article-publish"),
    path("<int:portal_id>/articles/<int:article_id>/archive/", content_views.ArticleArchiveView.as_view(), name="support-portal-article-archive"),
]
