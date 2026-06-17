from django.urls import path

from hub_platform.identity import company_views

urlpatterns = [
    path("departments/", company_views.department_list_view, name="department-list"),
    path("products/", company_views.product_list_view, name="product-list"),
    path("products/create/", company_views.create_product_view, name="product-create"),
    path("products/<int:product_id>/deactivate/", company_views.deactivate_product_view, name="product-deactivate"),
]
