from django.contrib import admin

from hub_platform.ai.models import AIAgent


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ("name", "product", "model", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "product__code")
