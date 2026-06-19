from django.urls import path

from hub_platform.products import views

urlpatterns = [
    path("products/", views.product_list_view, name="product-list"),
    path("products/create/", views.create_product_view, name="product-create"),
    path("products/<int:product_id>/", views.product_detail_view, name="product-detail"),
    path("products/<int:product_id>/update/", views.update_product_view, name="product-update"),
    path("products/<int:product_id>/activate/", views.activate_product_view, name="product-activate"),
    path("products/<int:product_id>/deactivate/", views.deactivate_product_view, name="product-deactivate"),
]
