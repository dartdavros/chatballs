from __future__ import annotations

import uuid
from django.core.exceptions import ValidationError
from django.db import models

from hub_platform.tenancy.models import TenantRelationModel
from hub_platform.support_portals.statuses import ArticleStatus, PortalStatus


class SupportPortal(TenantRelationModel):
    """Публичный Help Center, управляемый внутри отдела поддержки."""

    tenant_relation_fields = ("department", "widget_channel", "widget")
    department = models.ForeignKey(
        "identity.Department",
        on_delete=models.PROTECT,
        related_name="support_portals",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    hosted_domain = models.CharField(max_length=253, unique=True)
    custom_domain = models.CharField(max_length=253, blank=True, default="")
    custom_domain_verified_at = models.DateTimeField(null=True, blank=True)
    custom_domain_verification_token = models.UUIDField(
        default=uuid.uuid4, editable=False
    )
    name = models.CharField(max_length=255)
    default_locale = models.CharField(max_length=16, default="ru")
    status = models.CharField(
        max_length=16,
        choices=PortalStatus.choices,
        default=PortalStatus.DRAFT,
    )
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
    products = models.ManyToManyField(
        "products.Product",
        through="SupportPortalProduct",
        related_name="support_portals",
        blank=True,
    )

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=PortalStatus.values),
                name="support_portal_status_valid",
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
        from hub_platform.support_portals.addressing import clean_portal_domains
        from hub_platform.support_portals.widget_validation import validate_portal_widget

        clean_portal_domains(self)
        if self.department_id is not None and self.department.code != "support":
            raise ValidationError(
                {"department": "Support portal must belong to the support department"}
            )
        validate_portal_widget(self)


class SupportPortalProduct(TenantRelationModel):
    """Продукт портала и его authenticated support-маршрут."""

    tenant_relation_fields = ("portal", "product", "support_channel", "support_widget")
    portal = models.ForeignKey(
        SupportPortal,
        on_delete=models.CASCADE,
        related_name="product_links",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="support_portal_links",
    )
    support_channel = models.ForeignKey(
        "channels.Channel",
        on_delete=models.PROTECT,
        related_name="support_portal_routes",
        null=True,
        blank=True,
    )
    support_widget = models.ForeignKey(
        "webchat.WebChatWidget",
        on_delete=models.PROTECT,
        related_name="support_portal_routes",
        null=True,
        blank=True,
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "product__name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["portal", "product"],
                name="uniq_support_portal_product",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        from hub_platform.support_portals.widget_validation import (
            validate_product_support_widget,
        )

        validate_product_support_widget(self)
        if self.support_channel_id is None:
            return
        channel = self.support_channel
        if channel.product_id != self.product_id:
            raise ValidationError(
                {"support_channel": "Support channel must belong to the linked product"}
            )
        if channel.department_id is None or channel.department.code != "support":
            raise ValidationError(
                {"support_channel": "Support channel must belong to the support department"}
            )
        if (
            not channel.requires_authenticated_product_identity
            or channel.allow_anonymous_sessions
        ):
            raise ValidationError(
                {"support_channel": "Portal support route must require product identity"}
            )


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
