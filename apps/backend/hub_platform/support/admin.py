from django.contrib import admin

from hub_platform.support.models import ProductSupportContract, SupportIdentitySnapshot


@admin.register(ProductSupportContract)
class ProductSupportContractAdmin(admin.ModelAdmin):
    list_display = ("code", "version", "product", "organization", "status", "updated_at")
    list_filter = ("status", "organization")
    search_fields = ("code", "product__code", "product__name")
    filter_horizontal = ("allowed_channels",)


@admin.register(SupportIdentitySnapshot)
class SupportIdentitySnapshotAdmin(admin.ModelAdmin):
    list_display = ("subject_key", "product", "contract_code", "display_name", "verified_at")
    list_filter = ("product",)
    search_fields = ("subject_key", "display_name", "display_email", "search_text")
    readonly_fields = ("verified_at", "created_at", "payload_json", "token_jti_hash")
