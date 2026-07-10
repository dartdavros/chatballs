from django.contrib import admin

from hub_platform.channels.models import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "product", "department", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
