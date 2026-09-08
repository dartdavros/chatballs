from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from chatballs.support_portals.statuses import ArticleStatus, PortalStatus
from chatballs.support_portals.themes import (
    DEFAULT_PORTAL_THEME,
    PortalThemeScheme,
)
from chatballs.tenancy.models import TenantRelationModel


class SupportPortal(TenantRelationModel):
    """Публичный Help Center организации."""

    tenant_relation_fields = ("widget_channel", "widget")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    hosted_domain = models.CharField(max_length=253, unique=True)
    custom_domain = models.CharField(max_length=253, blank=True, default="")
    # Отметка технической проверки «домен ведёт на этот сервер». Подтверждения
    # владения доменом нет: домен и установка у одного владельца (README
    # дизайн-базлайна «Порталы», решение 6).
    custom_domain_verified_at = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=255)
    default_locale = models.CharField(max_length=16, default="ru")
    status = models.CharField(
        max_length=16,
        choices=PortalStatus.choices,
        default=PortalStatus.DRAFT,
    )
    # Тема хранится идентификатором из каталога фронтенда (ADR-CHATBALLS-0044):
    # список тем в БД не фиксируется, неизвестное значение деградирует до
    # темы по умолчанию при рендере публичной страницы.
    theme = models.CharField(max_length=64, default=DEFAULT_PORTAL_THEME)
    theme_scheme = models.CharField(
        max_length=16,
        choices=PortalThemeScheme.choices,
        default=PortalThemeScheme.LIGHT,
    )
    theme_settings = models.JSONField(default=dict, blank=True)
    transition_version = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    widget_channel = models.ForeignKey(
        "channels.Channel",
        on_delete=models.PROTECT,
        related_name="support_portal_widgets",
        null=True,
        blank=True,
    )
    widget = models.ForeignKey(
        "webchat.WebChatWidget",
        on_delete=models.PROTECT,
        related_name="support_portals",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=PortalStatus.values),
                name="support_portal_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(theme_scheme__in=PortalThemeScheme.values),
                name="support_portal_theme_scheme_valid",
            ),
            models.UniqueConstraint(
                fields=["custom_domain"],
                condition=~models.Q(custom_domain=""),
                name="uniq_support_portal_custom_domain",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.slug}"

    def clean(self) -> None:
        super().clean()
        from chatballs.support_portals.addressing import clean_portal_domains
        from chatballs.support_portals.themes import (
            validate_theme,
            validate_theme_settings,
        )
        from chatballs.support_portals.widget_validation import validate_portal_widget

        clean_portal_domains(self)
        validate_theme(self.theme)
        self.theme_settings = validate_theme_settings(self.theme_settings)
        validate_portal_widget(self)


class PortalCategory(TenantRelationModel):
    tenant_relation_fields = ("portal", "parent")
    portal = models.ForeignKey(
        SupportPortal,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["portal", "slug"],
                name="uniq_support_portal_category_slug",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.parent_id is not None and self.parent.portal_id != self.portal_id:
            raise ValidationError({"parent": "Parent category belongs to another portal"})
        current = self.parent
        visited = {self.pk} if self.pk else set()
        while current is not None:
            if current.pk in visited:
                raise ValidationError({"parent": "Category cycle is not allowed"})
            visited.add(current.pk)
            current = current.parent


class PortalArticle(TenantRelationModel):
    tenant_relation_fields = ("portal", "category", "published_revision")
    portal = models.ForeignKey(
        SupportPortal,
        on_delete=models.CASCADE,
        related_name="articles",
    )
    category = models.ForeignKey(
        PortalCategory,
        on_delete=models.PROTECT,
        related_name="articles",
    )
    slug = models.SlugField(max_length=96)
    locale = models.CharField(max_length=16, default="ru")
    status = models.CharField(
        max_length=16,
        choices=ArticleStatus.choices,
        default=ArticleStatus.DRAFT,
    )
    published_revision = models.ForeignKey(
        "PortalArticleRevision",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["slug", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["portal", "locale", "slug"],
                name="uniq_support_portal_article_slug",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=ArticleStatus.values),
                name="support_portal_article_status_valid",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.category_id is not None and self.category.portal_id != self.portal_id:
            raise ValidationError({"category": "Category belongs to another portal"})
        if (
            self.published_revision_id is not None
            and self.published_revision.article_id != self.pk
        ):
            raise ValidationError(
                {"published_revision": "Published revision belongs to another article"}
            )


class PortalArticleRevision(TenantRelationModel):
    tenant_relation_fields = ("article",)
    article = models.ForeignKey(
        PortalArticle,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    revision = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    summary = models.CharField(max_length=500, blank=True)
    content = models.TextField()
    # Автор редакции показывается в рейке версий редактора статьи (кадр PT7).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "revision"],
                name="uniq_support_portal_article_revision",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gt=0),
                name="support_portal_article_revision_positive",
            ),
        ]


def article_file_upload_path(instance: PortalArticleFile, filename: str) -> str:
    organization = instance.article.organization
    return (
        f"organizations/{organization.public_id}/portal-articles/"
        f"{instance.article_id}/{instance.public_id}/{filename}"
    )


class PortalArticleFile(TenantRelationModel):
    """Файл статьи портала: картинка или документ, вставленный в Markdown.

    Ссылка публичная и защищена непредсказуемым UUID: файл открывается
    посетителем портала, у которого нет аутентификации хаба (как у вложений
    знаний, ADR-CHATBALLS-0023).
    """

    tenant_relation_fields = ("article",)
    article = models.ForeignKey(
        PortalArticle,
        on_delete=models.CASCADE,
        related_name="files",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file = models.FileField(upload_to=article_file_upload_path, max_length=512)
    # Оригинальное имя уникально в рамках статьи: текст статьи ссылается на файл
    # по ссылке, а редактор показывает имя в рейке файлов.
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=128, blank=True)
    size = models.PositiveBigIntegerField(default=0)
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
        constraints = [
            models.UniqueConstraint(
                fields=["article", "original_name"],
                name="uniq_portal_article_file_name",
            )
        ]

    def __str__(self) -> str:
        return f"portal-file:{self.article_id}/{self.original_name}"

    def public_path(self) -> str:
        """Ссылка для Markdown статьи — относительная.

        Портал открывается на своём домене, а страница отдаётся с CSP
        ``img-src 'self'``: абсолютная ссылка на домен установки была бы для
        неё чужим origin и картинка не отобразилась бы. Относительный путь
        работает и на портале, и в предпросмотре редактора.
        """
        from django.urls import reverse

        return reverse("portal-article-file", kwargs={"public_id": self.public_id})

    def public_url(self) -> str:
        # Абсолютная ссылка — для мест, где нужен полный адрес (письма,
        # сообщения в мессенджер): там относительный путь бесполезен.
        from chatballs.identity.instance_settings import public_base_url

        return public_base_url() + self.public_path()


class PortalArticleFeedback(TenantRelationModel):
    tenant_relation_fields = ("article",)
    article = models.ForeignKey(
        PortalArticle,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
