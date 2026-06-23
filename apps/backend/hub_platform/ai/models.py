from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

# Один основной sales-агент на продукт (ADR-HUB-0007).
DEFAULT_AI_MODEL = "openai/gpt-4o-mini"


class AIAgent(models.Model):
    product = models.OneToOneField("products.Product", on_delete=models.PROTECT, related_name="ai_agent")
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    model = models.CharField(max_length=128, default=DEFAULT_AI_MODEL)
    model_params = models.JSONField(default=dict, blank=True)
    allowed_tools = models.JSONField(default=list, blank=True)
    limits = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.product.code}:agent"


# --- Knowledge & prompt documents (ADR-HUB-0005) ---


class DocumentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    PUBLISHED = "PUBLISHED", "Опубликован"
    ARCHIVED = "ARCHIVED", "Архив"


class KnowledgeCategory(models.TextChoices):
    OVERVIEW = "OVERVIEW", "Обзор продукта"
    AUDIENCE = "AUDIENCE", "Целевая аудитория"
    COMMERCIAL = "COMMERCIAL", "Коммерческая модель"
    TECHNICAL = "TECHNICAL", "Техническая информация"
    FAQ = "FAQ", "FAQ"
    OBJECTIONS = "OBJECTIONS", "Возражения"
    LIMITATIONS = "LIMITATIONS", "Ограничения"


class PromptCategory(models.TextChoices):
    SYSTEM = "SYSTEM", "Системный промпт"
    QUALIFICATION = "QUALIFICATION", "Квалификация"
    SALES_BEHAVIOR = "SALES_BEHAVIOR", "Поведение в продаже"
    OPERATOR_HANDOFF = "OPERATOR_HANDOFF", "Передача оператору"


class InclusionMode(models.TextChoices):
    MANDATORY = "MANDATORY", "Обязательное включение"
    RETRIEVAL = "RETRIEVAL", "Доступно для retrieval"


class _BaseDocument(models.Model):
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="%(class)ss")
    code = models.SlugField(max_length=64)
    title = models.CharField(max_length=255)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class KnowledgeDocument(_BaseDocument):
    category = models.CharField(max_length=32, choices=KnowledgeCategory.choices)
    inclusion_mode = models.CharField(max_length=16, choices=InclusionMode.choices, default=InclusionMode.RETRIEVAL)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "code"], name="uniq_knowledge_doc_product_code")]

    def __str__(self) -> str:
        return f"knowledge:{self.product_id}/{self.code}"


class PromptDocument(_BaseDocument):
    category = models.CharField(max_length=32, choices=PromptCategory.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["product", "code"], name="uniq_prompt_doc_product_code")]

    def __str__(self) -> str:
        return f"prompt:{self.product_id}/{self.code}"


class _BaseDocumentVersion(models.Model):
    version = models.PositiveIntegerField()
    content = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ["-version"]

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk:
            current = type(self).objects.get(pk=self.pk)
            if current.version != self.version or current.content != self.content:
                raise ValidationError("Document version content is immutable")
        super().save(*args, **kwargs)


class KnowledgeDocumentVersion(_BaseDocumentVersion):
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="versions")

    class Meta(_BaseDocumentVersion.Meta):
        constraints = [models.UniqueConstraint(fields=["document", "version"], name="uniq_knowledge_version")]


class PromptDocumentVersion(_BaseDocumentVersion):
    document = models.ForeignKey(PromptDocument, on_delete=models.CASCADE, related_name="versions")

    class Meta(_BaseDocumentVersion.Meta):
        constraints = [models.UniqueConstraint(fields=["document", "version"], name="uniq_prompt_version")]
