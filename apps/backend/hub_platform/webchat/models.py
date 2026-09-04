import secrets

from django.core.exceptions import ValidationError
from django.db import models

from hub_platform.tenancy.models import TenantRelationModel


def generate_widget_public_key() -> str:
    return f"wgt_{secrets.token_urlsafe(24)}"


class WebChatWidgetMode(models.TextChoices):
    ANONYMOUS = "ANONYMOUS", "Анонимный"
    AUTHENTICATED_PRODUCT = "AUTHENTICATED_PRODUCT", "Авторизованный продукт"


class WebChatWidgetStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    PUBLISHED = "PUBLISHED", "Опубликован"
    DISABLED = "DISABLED", "Отключён"


class WebChatWidget(TenantRelationModel):
    """Публичная Web Chat entry point поверх одного WEB-подключения."""

    tenant_relation_fields = ("integration",)
    integration = models.OneToOneField(
        "integrations.Integration",
        on_delete=models.CASCADE,
        related_name="web_chat_widget",
    )
    code = models.SlugField(max_length=64)
    public_key = models.CharField(
        max_length=64,
        unique=True,
        default=generate_widget_public_key,
        editable=False,
    )
    name = models.CharField(max_length=255)
    mode = models.CharField(
        max_length=32,
        choices=WebChatWidgetMode.choices,
        default=WebChatWidgetMode.ANONYMOUS,
    )
    status = models.CharField(
        max_length=16,
        choices=WebChatWidgetStatus.choices,
        default=WebChatWidgetStatus.DRAFT,
    )
    allowed_origins = models.JSONField(default=list, blank=True)
    presentation_config = models.JSONField(default=dict, blank=True)
    consent_config = models.JSONField(default=dict, blank=True)
    anti_abuse_config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="uniq_web_chat_widget_org_code",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization_id}/{self.code}"

    def clean(self) -> None:
        super().clean()
        integration = self.integration
        if integration.provider != "WEB":
            raise ValidationError({"integration": "Web Chat widget requires a WEB integration"})
        channel = integration.channel
        if channel is None:
            raise ValidationError({"integration": "Web Chat widget requires a channel"})
        if self.mode == WebChatWidgetMode.AUTHENTICATED_PRODUCT:
            if (
                channel.product_id is None
                or not channel.requires_authenticated_product_identity
                or channel.allow_anonymous_sessions
                or channel.allow_self_reported_contact
            ):
                raise ValidationError({"mode": "Authenticated widget requires a product support channel"})
        elif channel.requires_authenticated_product_identity or not channel.allow_anonymous_sessions:
            raise ValidationError({"mode": "Anonymous widget requires an anonymous channel"})

# Анонимная браузерная сессия Web Chat (SPEC-HUB-0003 §7). Храним только hash
# токена; токен живёт в браузере и идентифицирует ConnectionIdentity канала.


class WebSession(TenantRelationModel):
    tenant_relation_fields = ("connection", "identity", "widget")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    connection = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="web_sessions")
    widget = models.ForeignKey(WebChatWidget, on_delete=models.PROTECT, related_name="sessions")
    identity = models.ForeignKey("conversations.ConnectionIdentity", on_delete=models.CASCADE, related_name="web_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"websession:{self.identity_id}"
