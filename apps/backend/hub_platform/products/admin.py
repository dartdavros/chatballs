from django.contrib import admin

from hub_platform.products.models import MarketplacePublication, Offer, Price, Product, ProductDepartment


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "organization", "status", "site_url"]
    list_filter = ["organization", "status"]
    search_fields = ["code", "name"]


@admin.register(ProductDepartment)
class ProductDepartmentAdmin(admin.ModelAdmin):
    list_display = ["product", "department", "created_at"]
    list_filter = ["department__organization", "department"]


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "product", "fulfillment_type", "payment_type", "is_active"]
    list_filter = ["product", "fulfillment_type", "payment_type", "is_active"]
    search_fields = ["code", "name", "product__name"]


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ["offer", "version", "amount_minor", "currency", "billing_period", "is_active"]
    list_filter = ["currency", "billing_period", "is_active"]

    def has_change_permission(self, request, obj=None):
        return obj is None


@admin.register(MarketplacePublication)
class MarketplacePublicationAdmin(admin.ModelAdmin):
    list_display = ["marketplace_code", "price", "status", "published_at"]
    list_filter = ["marketplace_code", "status"]
