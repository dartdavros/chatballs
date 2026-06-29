from django.contrib import admin

from hub_platform.orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "contact", "product", "payment_status", "fulfillment_status", "amount_minor", "created_at")
    list_filter = ("payment_status", "fulfillment_status", "organization")
    search_fields = ("id", "contact__name")
    inlines = [OrderItemInline]
