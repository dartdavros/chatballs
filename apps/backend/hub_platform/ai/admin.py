from django.contrib import admin

from hub_platform.ai.models import AIAgent, KnowledgeDocument, ProductAIRelease, PromptDocument


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "model", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "product__code")


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "category", "inclusion_mode", "is_enabled")
    list_filter = ("category", "inclusion_mode", "is_enabled")
    search_fields = ("title", "code", "product__code")


@admin.register(PromptDocument)
class PromptDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "product", "category", "is_enabled")
    list_filter = ("category", "is_enabled")
    search_fields = ("title", "code", "product__code")


@admin.register(ProductAIRelease)
class ProductAIReleaseAdmin(admin.ModelAdmin):
    list_display = ("product", "version", "status", "model", "published_at")
    list_filter = ("status",)
    search_fields = ("product__code",)
