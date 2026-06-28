from django.contrib import admin

from hub_platform.conversations.models import Contact, Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "contact", "lifecycle", "control_mode", "last_activity_at")
    list_filter = ("lifecycle", "control_mode")


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "organization", "created_at")
    search_fields = ("name",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "author_type", "created_at")
    list_filter = ("author_type",)
