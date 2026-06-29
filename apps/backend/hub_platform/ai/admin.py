from django.contrib import admin

from hub_platform.ai.models import AIAgent, ChannelAIRelease, KnowledgeDocument, PromptDocument


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "model", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "channel__code")


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "scope", "product", "category", "inclusion_mode", "is_enabled")
    list_filter = ("scope", "category", "inclusion_mode", "is_enabled")
    search_fields = ("title", "code", "product__code")


@admin.register(PromptDocument)
class PromptDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "scope", "product", "category", "is_enabled")
    list_filter = ("scope", "category", "is_enabled")
    search_fields = ("title", "code", "product__code")


@admin.register(ChannelAIRelease)
class ChannelAIReleaseAdmin(admin.ModelAdmin):
    list_display = ("channel", "version", "status", "model", "published_at")
    list_filter = ("status",)
    search_fields = ("channel__code",)
