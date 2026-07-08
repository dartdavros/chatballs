from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.db import models

# Отдел поддержки — authenticated in-product чат (ADR-HUB-0022, SPEC-HUB-0010/0011).
# Hub не владеет бизнес-моделью клиента продукта: каждый продукт публикует
# версионированный ProductSupportIdentityContract, а Hub хранит проверенный
# SupportIdentitySnapshot после проверки Product Support Token. Raw token нигде
# не сохраняется — только короткий хэш jti для audit/replay.

# Формат code контракта: <product_code>.support.v<major> (SPEC-HUB-0011 §3).
_CONTRACT_CODE_RE = re.compile(
    r"^(?P<product_code>[a-z0-9-]+)\.support\.v(?P<version>[1-9][0-9]*)$"
)


class ContractStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    ACTIVE = "ACTIVE", "Активен"
    DEPRECATED = "DEPRECATED", "Устаревший"
    DISABLED = "DISABLED", "Отключён"


class ProductSupportContract(models.Model):
    """Версионированный контракт идентификации клиента поддержки продукта.

    Описывает JSON Schema payload токена, mapping identity, карточки оператора,
    AI-visible context, search и sensitive fields (SPEC-HUB-0011 §5).
    """

    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="support_contracts",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="support_contracts",
    )
    code = models.SlugField(max_length=64)
    version = models.PositiveSmallIntegerField()
    status = models.CharField(
        max_length=16,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
    )
    allowed_channels = models.ManyToManyField(
        "channels.Channel",
        related_name="allowed_support_contracts",
        blank=True,
    )
    schema_json = models.JSONField(default=dict, blank=True)
    identity_mapping_json = models.JSONField(default=dict, blank=True)
    operator_ui_json = models.JSONField(default=dict, blank=True)
    ai_context_json = models.JSONField(default=dict, blank=True)
    search_mapping_json = models.JSONField(default=dict, blank=True)
    sensitive_fields_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="uniq_support_contract_org_code",
            ),
        ]
        indexes = [models.Index(fields=["product", "status"])]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.code}"

    def clean(self) -> None:
        super().clean()
        if self.product.organization_id != self.organization_id:
            raise ValidationError({"product": "Product must belong to the same organization"})
        match = _CONTRACT_CODE_RE.match(self.code)
        if match is None:
            raise ValidationError(
                {"code": "Contract code must be '<product_code>.support.v<major>'"}
            )
        if match.group("product_code") != self.product.code:
            raise ValidationError({"code": "Contract code product part must match product code"})
        if self.version != int(match.group("version")):
            raise ValidationError({"version": "Version must match the major in contract code"})


class SupportIdentitySnapshot(models.Model):
    """Проверенный снимок identity/context клиента поддержки (SPEC-HUB-0011 §13).

    Исторический снимок: если продукт позже изменил данные или структуру payload,
    старый диалог остаётся читаемым в контексте того обращения. Raw token не
    сохраняется — только хэш jti для audit/replay-обнаружения.
    """

    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="support_identity_snapshots",
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="support_identity_snapshots",
    )
    contract = models.ForeignKey(
        ProductSupportContract,
        on_delete=models.PROTECT,
        related_name="snapshots",
    )
    contract_code = models.CharField(max_length=64)
    subject_key = models.CharField(max_length=128, db_index=True)
    account_key = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    display_name = models.CharField(max_length=255, blank=True)
    display_email = models.CharField(max_length=255, blank=True)
    payload_json = models.JSONField(default=dict, blank=True)
    operator_context_json = models.JSONField(default=dict, blank=True)
    ai_context_json = models.JSONField(default=dict, blank=True)
    search_text = models.TextField(blank=True)
    verified_at = models.DateTimeField(auto_now_add=True, db_index=True)
    token_issued_at = models.DateTimeField()
    token_expires_at = models.DateTimeField()
    token_jti_hash = models.CharField(max_length=64, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["product", "subject_key"]),
            models.Index(fields=["product", "account_key"]),
        ]

    def __str__(self) -> str:
        return f"snapshot:{self.id}/{self.subject_key}"
