import secrets
import uuid
from pathlib import PurePath

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from chatballs.tenancy.models import TenantRelationModel


def generate_widget_public_key() -> str:
    return f"wgt_{secrets.token_urlsafe(24)}"


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
        if not channel.allow_anonymous_sessions:
            raise ValidationError({"integration": "Widget requires a channel with anonymous sessions"})

# Анонимная браузерная сессия Web Chat (SPEC-CHATBALLS-0003 §7). Храним только hash
# токена; токен живёт в браузере и идентифицирует ConnectionIdentity канала.


class WebSession(TenantRelationModel):
    tenant_relation_fields = ("connection", "identity", "widget")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    connection = models.ForeignKey("integrations.Integration", on_delete=models.CASCADE, related_name="web_sessions")
    widget = models.ForeignKey(WebChatWidget, on_delete=models.PROTECT, related_name="sessions")
    identity = models.ForeignKey("conversations.ConnectionIdentity", on_delete=models.CASCADE, related_name="web_sessions")
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    consent_version = models.CharField(max_length=255, blank=True, default="")
    consent_accepted_at = models.DateTimeField(null=True, blank=True)
    consent_form_revision = models.CharField(max_length=64, blank=True, default="")

    def __str__(self) -> str:
        return f"websession:{self.identity_id}"


def widget_asset_upload_path(instance: "WidgetAsset", filename: str) -> str:
    organization = instance.integration.organization
    return (
        f"organizations/{organization.public_id}/webchat/"
        f"{instance.integration_id}/{instance.public_id}{PurePath(filename).suffix}"
    )


class WidgetAsset(TenantRelationModel):
    """Иконка кнопки или шапки виджета (SPEC-0021 R-3).

    Файл показывается на чужом сайте без сессии, поэтому ссылка публичная и
    защищена непредсказуемым UUID, как у файлов статей портала. Каждая
    загрузка — новый ключ: прежний адрес не перезаписывается.
    """

    tenant_relation_fields = ("integration",)
    integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.CASCADE,
        related_name="widget_assets",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file = models.FileField(upload_to=widget_asset_upload_path, max_length=512)
    content_type = models.CharField(max_length=64)
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"widget-asset:{self.integration_id}/{self.public_id}"


from chatballs.webchat.observation_models import VisitorObservation  # noqa: E402,F401
from chatballs.webchat.proactive_models import SiteEventLaunch  # noqa: E402,F401
