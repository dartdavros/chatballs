from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from hub_platform.identity.crypto import EncryptedCharField
from hub_platform.tenancy.models import TenantRelationModel


class ProductStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Активен"
    DISABLED = "DISABLED", "Неактивен"


class Product(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="products")
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=32, choices=ProductStatus.choices, default=ProductStatus.ACTIVE)
    site_url = models.URLField(blank=True)
    # Содержательное описание продукта живёт в Знаниях (ADR-HUB-0023): продукт —
    # скрытая техническая запись-якорь для каналов, поддержки и webchat (ADR-HUB-0041).
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


class ProductDepartment(TenantRelationModel):
    tenant_relation_fields = ("product", "department")
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
