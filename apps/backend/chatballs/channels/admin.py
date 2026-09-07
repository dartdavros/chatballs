from django.contrib import admin

from chatballs.channels.models import Channel


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "group", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
