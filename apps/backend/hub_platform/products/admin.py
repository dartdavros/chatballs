from django.contrib import admin

from hub_platform.products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "organization", "status", "site_url"]
    list_filter = ["organization", "status"]
    search_fields = ["code", "name"]
