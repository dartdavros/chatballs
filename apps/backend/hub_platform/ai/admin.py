from django.contrib import admin

from hub_platform.ai.models import AIAgent, Knowledge, KnowledgeAttachment


class KnowledgeAttachmentInline(admin.TabularInline):
    model = KnowledgeAttachment
    extra = 0
    readonly_fields = ("public_id", "size", "content_type", "created_at")


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "model", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "channel__code")
    filter_horizontal = ("knowledge_items",)


@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("title", "description")
    inlines = [KnowledgeAttachmentInline]
