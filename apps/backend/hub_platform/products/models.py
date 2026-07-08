from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from hub_platform.identity.crypto import EncryptedCharField


class ProductStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Активен"
    DISABLED = "DISABLED", "Неактивен"


class Product(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="products")
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=ProductStatus.choices, default=ProductStatus.ACTIVE)
    site_url = models.URLField(blank=True)
    summary = models.CharField(max_length=500, blank=True)
    sales_description = models.TextField(blank=True)
    # SHA-256 токена бэкенда продукта для вебхука заказов (ADR-HUB-0018). Сам токен
    # не хранится — выдаётся один раз командой issue_product_ingest_token.
    ingest_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    # Секрет проверки Product Support Token (ADR-HUB-0022, SPEC-HUB-0011 §4.3).
    # HS256-секрет для подписи токена поддержки; хранится зашифрованным (Fernet),
    # в API не отдаётся. Продукт использует его для подписи in-product support token.
    support_token_secret = EncryptedCharField(max_length=512, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_product"
        constraints = [models.UniqueConstraint(fields=["organization", "code"], name="uniq_product_org_code")]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.code}"


class ProductDepartment(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="department_links")
    department = models.ForeignKey("identity.Department", on_delete=models.PROTECT, related_name="product_links")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "department"], name="uniq_product_department")
        ]

    def clean(self) -> None:
        if self.product.organization_id != self.department.organization_id:
            raise ValidationError("Product and department must belong to the same organization")


class OfferFulfillmentType(models.TextChoices):
    SAAS_ACCESS = "SAAS_ACCESS", "SaaS-доступ"
    BOX_LICENSE = "BOX_LICENSE", "Коробочная лицензия"
    SUPPORT_EXTENSION = "SUPPORT_EXTENSION", "Продление поддержки"


class OfferPaymentType(models.TextChoices):
    ONE_TIME = "ONE_TIME", "Разовая оплата"
    SUBSCRIPTION = "SUBSCRIPTION", "Подписка"


class Offer(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="offers")
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    fulfillment_type = models.CharField(max_length=32, choices=OfferFulfillmentType.choices)
    payment_type = models.CharField(max_length=32, choices=OfferPaymentType.choices)
    primary_box_offer = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="support_extensions",
        null=True,
        blank=True,
    )
    access_schema = models.JSONField(default=dict, blank=True)
    fiscal_name = models.CharField(max_length=255, blank=True)
    fiscal_attributes = models.JSONField(default=dict, blank=True)
    subscription_rules = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    ai_offerable = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "code"], name="uniq_offer_product_code"),
            models.CheckConstraint(
                condition=(
                    Q(fulfillment_type=OfferFulfillmentType.SUPPORT_EXTENSION, primary_box_offer__isnull=False)
                    | ~Q(fulfillment_type=OfferFulfillmentType.SUPPORT_EXTENSION)
                ),
                name="support_offer_requires_primary_box",
            ),
        ]

    def clean(self) -> None:
        if self.fulfillment_type == OfferFulfillmentType.SUPPORT_EXTENSION:
            if self.primary_box_offer is None:
                raise ValidationError({"primary_box_offer": "Support extension requires a box offer"})
            if self.primary_box_offer.product_id != self.product_id:
                raise ValidationError({"primary_box_offer": "Offers must belong to the same product"})
            if self.primary_box_offer.fulfillment_type != OfferFulfillmentType.BOX_LICENSE:
                raise ValidationError({"primary_box_offer": "Referenced offer must be a box license"})
        elif self.primary_box_offer_id is not None:
            raise ValidationError({"primary_box_offer": "Only support extensions reference a box offer"})


class BillingPeriod(models.TextChoices):
    ONE_TIME = "ONE_TIME", "Разово"
    MONTH = "MONTH", "Месяц"
    YEAR = "YEAR", "Год"


class Price(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.PROTECT, related_name="prices")
    version = models.PositiveIntegerField()
    amount_minor = models.PositiveBigIntegerField()
    currency = models.CharField(max_length=3, default="RUB")
    billing_period = models.CharField(max_length=16, choices=BillingPeriod.choices)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["offer_id", "billing_period", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "currency", "billing_period", "version"],
                name="uniq_price_offer_period_version",
            ),
            models.UniqueConstraint(
                fields=["offer", "currency", "billing_period"],
                condition=Q(is_active=True),
                name="uniq_active_price_offer_currency_period",
            ),
            models.CheckConstraint(condition=Q(amount_minor__gte=0), name="price_amount_non_negative"),
        ]

    def save(self, *args: object, **kwargs: object) -> None:
        if self.pk:
            current = Price.objects.get(pk=self.pk)
            immutable_fields = ("offer_id", "version", "amount_minor", "currency", "billing_period", "valid_from")
            if any(getattr(current, field) != getattr(self, field) for field in immutable_fields):
                raise ValidationError("Price version data is immutable")
        super().save(*args, **kwargs)


class MarketplacePublicationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    PUBLISHED = "PUBLISHED", "Опубликовано"
    DISABLED = "DISABLED", "Отключено"


class MarketplacePublication(models.Model):
    marketplace_code = models.SlugField(max_length=64)
    price = models.ForeignKey(Price, on_delete=models.PROTECT, related_name="marketplace_publications")
    status = models.CharField(
        max_length=16,
        choices=MarketplacePublicationStatus.choices,
        default=MarketplacePublicationStatus.DRAFT,
    )
    external_reference = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["marketplace_code", "price"],
                name="uniq_marketplace_price_publication",
            )
        ]
