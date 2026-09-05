from django.contrib import admin

from chatballs.notifications.models import Notification, NotificationRead


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("type", "audience", "level", "title", "organization", "created_at")
    list_filter = ("type", "audience", "level")
    search_fields = ("title", "body", "dedup_key")


@admin.register(NotificationRead)
class NotificationReadAdmin(admin.ModelAdmin):
    list_display = ("notification", "user", "read_at")
