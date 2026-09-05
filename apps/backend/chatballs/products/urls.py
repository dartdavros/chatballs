from django.urls import path

from chatballs.products import views

urlpatterns = [
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/create/", views.ProductCreateView.as_view(), name="product-create"),
    path("products/<int:product_id>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("products/<int:product_id>/update/", views.ProductUpdateView.as_view(), name="product-update"),
    path("products/<int:product_id>/activate/", views.ProductActivateView.as_view(), name="product-activate"),
    path("products/<int:product_id>/deactivate/", views.ProductDeactivateView.as_view(), name="product-deactivate"),
]
