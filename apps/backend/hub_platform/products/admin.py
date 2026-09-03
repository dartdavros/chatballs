from django.contrib import admin

from hub_platform.products.models import Product, ProductDepartment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "organization", "status", "site_url"]
    list_filter = ["organization", "status"]
    search_fields = ["code", "name"]


@admin.register(ProductDepartment)
class ProductDepartmentAdmin(admin.ModelAdmin):
    list_display = ["product", "department", "created_at"]
    list_filter = ["department__organization", "department"]
