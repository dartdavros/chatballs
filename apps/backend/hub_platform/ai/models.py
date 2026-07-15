import uuid

from django.db import models
from pgvector.django import VectorField

from hub_platform.tenancy.models import TenantRelationModel

# Один основной агент на канал обработки (ADR-HUB-0019, ADR-HUB-0023).
DEFAULT_AI_MODEL = "anthropic/claude-sonnet-4.6"


# --- Знания: плоская библиотека организации с вложениями (ADR-HUB-0023) ---


class Knowledge(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="knowledge_items")
    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    content = models.TextField(blank=True)  # Markdown
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name_plural = "knowledge"

    def __str__(self) -> str:
        return f"knowledge:{self.organization_id}/{self.title}"


def attachment_upload_path(instance: "KnowledgeAttachment", filename: str) -> str:
    organization = instance.knowledge.organization
    return (
        f"organizations/{organization.public_id}/knowledge/"
        f"{instance.knowledge_id}/{instance.public_id}/{filename}"
    )


class KnowledgeAttachment(TenantRelationModel):
    tenant_relation_fields = ("knowledge",)
    knowledge = models.ForeignKey(Knowledge, on_delete=models.CASCADE, related_name="attachments")
    # Непредсказуемый идентификатор публичной ссылки скачивания (ADR-HUB-0023):
    # агент может отдать ссылку клиенту в мессенджер, где нет аутентификации Hub.
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file = models.FileField(upload_to=attachment_upload_path, max_length=512)
    # Оригинальное имя сохраняется и уникально в рамках знания: текст знания
    # ссылается на вложение по имени.
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    # Текст, извлечённый из файла (md/txt/pdf/docx) для retrieval-индексации.
    extracted_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["original_name"]
        constraints = [models.UniqueConstraint(fields=["knowledge", "original_name"], name="uniq_attachment_knowledge_name")]

    def __str__(self) -> str:
        return f"attachment:{self.knowledge_id}/{self.original_name}"

    def public_url(self) -> str:
        # Абсолютная ссылка скачивания: уходит клиентам в мессенджеры, поэтому
        # строится от публичного адреса Hub, а не от request.
        from django.conf import settings
        from django.urls import reverse

        path = reverse("ai-attachment-download", kwargs={"public_id": self.public_id})
        return settings.HUB_PUBLIC_BASE_URL.rstrip("/") + path


class KnowledgeFragment(TenantRelationModel):
    tenant_relation_fields = ("knowledge",)
    # Чанк знания + его эмбеддинг (pgvector). ADR-HUB-0016. Перестраивается при
    # каждом изменении содержимого или вложений знания.
    knowledge = models.ForeignKey(Knowledge, on_delete=models.CASCADE, related_name="fragments")
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    # Размерность не фиксируется: совместимость локального и production embedding-провайдера.
    embedding = VectorField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["knowledge_id", "chunk_index"]
        constraints = [models.UniqueConstraint(fields=["knowledge", "chunk_index"], name="uniq_fragment_knowledge_chunk")]

    def __str__(self) -> str:
        return f"fragment:{self.knowledge_id}/{self.chunk_index}"


# --- Агент канала: одна сущность, без релизов (ADR-HUB-0023) ---


class AIAgent(TenantRelationModel):
    tenant_relation_fields = ("channel",)
    channel = models.OneToOneField("channels.Channel", on_delete=models.CASCADE, related_name="ai_agent")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    model = models.CharField(max_length=128, default=DEFAULT_AI_MODEL)
    model_params = models.JSONField(default=dict, blank=True)
    # Инструкции из трёх частей; системный промпт собирается в этом порядке.
    persona = models.TextField(blank=True)  # кто он и что он
    tone = models.TextField(blank=True)  # как он должен говорить
    instructions = models.TextField(blank=True)  # правила работы
    # Выбор знаний из библиотеки организации.
    knowledge_items = models.ManyToManyField(Knowledge, blank=True, related_name="agents")
    allowed_tools = models.JSONField(default=list, blank=True)
    # Единственный поддерживаемый лимит — дневной бюджет dailyCostUsd (центы USD).
    limits = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.channel.code}:agent"


# --- LLM usage accounting (tokens, cost) ---


class LlmInvocationStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "Успех"
    ERROR = "ERROR", "Ошибка"
    BLOCKED = "BLOCKED", "Заблокировано лимитом"


class LlmInvocation(TenantRelationModel):
    tenant_relation_fields = ("channel", "product")
    # Учёт по каналу (ADR-HUB-0019) и/или продукту, если канал продуктовый.
    channel = models.ForeignKey("channels.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="ai_invocations")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="ai_invocations", null=True, blank=True)
    purpose = models.CharField(max_length=64)
    operation = models.CharField(max_length=16)  # chat | embedding
    model = models.CharField(max_length=128, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    cost_micros = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    latency_ms = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=LlmInvocationStatus.choices, default=LlmInvocationStatus.SUCCESS)
    error = models.TextField(blank=True)
    used_fragment_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["channel", "created_at"])]

    def __str__(self) -> str:
        return f"llm:{self.channel_id}/{self.operation}/{self.status}"
