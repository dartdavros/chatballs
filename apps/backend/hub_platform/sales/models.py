from __future__ import annotations

from django.db import models
from django.db.models import F, Q

# Учёт внешних продаж (ADR-HUB-0025, SPEC-HUB-0014). Hub НЕ владеет заказом,
# оплатой, чеком, подпиской или выдачей продукта — этим владеет backend продукта.
# Здесь ведётся нормализованная проекция состоявшейся продажи (Sale), append-only
# журнал событий (SaleEvent) и связь продажи с диалогом/клиентом/автором.


class Environment(models.TextChoices):
    LOCAL = "LOCAL", "Local"
    STAGING = "STAGING", "Staging"
    PRODUCTION = "PRODUCTION", "Production"


class SourceType(models.TextChoices):
    PRODUCT_API = "PRODUCT_API", "Product Sales API"
    MANUAL = "MANUAL", "Ручная фиксация"
    LEGACY_IMPORT = "LEGACY_IMPORT", "Импорт legacy"


class SaleStatus(models.TextChoices):
    CONFIRMED = "CONFIRMED", "Подтверждена"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Частичный возврат"
    REFUNDED = "REFUNDED", "Возврат"
    CANCELLED = "CANCELLED", "Отменена"


class SaleEventType(models.TextChoices):
    CONFIRMED = "sale.confirmed", "Подтверждение"
    CORRECTED = "sale.corrected", "Исправление"
    CANCELLED = "sale.cancelled", "Отмена"
    PARTIALLY_REFUNDED = "sale.partially_refunded", "Частичный возврат"
    REFUNDED = "sale.refunded", "Возврат"
    LEGACY_IMPORTED = "sale.legacy_imported", "Импорт legacy"


# Типы событий внешнего Product Sales API (без внутреннего legacy_imported).
PRODUCT_API_EVENT_TYPES = frozenset(
    {
        SaleEventType.CONFIRMED,
        SaleEventType.CORRECTED,
        SaleEventType.CANCELLED,
        SaleEventType.PARTIALLY_REFUNDED,
        SaleEventType.REFUNDED,
    }
)


class ProcessingStatus(models.TextChoices):
    RECEIVED = "RECEIVED", "Принято"
    APPLIED = "APPLIED", "Применено"
    REJECTED = "REJECTED", "Отклонено"
    RETRYABLE = "RETRYABLE", "Повтор возможен"


class AttributionMethod(models.TextChoices):
    ATTRIBUTION_TOKEN = "ATTRIBUTION_TOKEN", "Attribution token"
    EXTERNAL_IDENTITY = "EXTERNAL_IDENTITY", "External identity"
    CONTACT_MATCH = "CONTACT_MATCH", "Совпадение контакта"
    MANUAL = "MANUAL", "Ручная привязка"
    NONE = "NONE", "Без атрибуции"


class ActorType(models.TextChoices):
    AI_AGENT = "AI_AGENT", "AI-агент"
    EMPLOYEE = "EMPLOYEE", "Сотрудник"
    # Historical read compatibility (SPEC-HUB-0018 §10). New events never use these.
    OPERATOR = "OPERATOR", "Оператор"
    OWNER = "OWNER", "Владелец"


class SalesSourceType(models.TextChoices):
    PRODUCT_API = "PRODUCT_API", "Product Sales API"


class SalesSourceStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Активен"
    READ_ONLY = "READ_ONLY", "Только чтение"
    DISABLED = "DISABLED", "Отключён"


class SalesSource(models.Model):
    """Автоматический источник внешних фактов продаж (SPEC-HUB-0014 §3.5).

    Не является integrations.Integration (ADR-HUB-0020): Product Sales API — входная
    граница sales-домена, а не канал коммуникации. Credential хранится как SHA-256.
    """

    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="sales_sources")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="sales_sources")
    code = models.SlugField(max_length=64)
    type = models.CharField(max_length=32, choices=SalesSourceType.choices, default=SalesSourceType.PRODUCT_API)
    environment = models.CharField(max_length=16, choices=Environment.choices, default=Environment.PRODUCTION)
    status = models.CharField(max_length=16, choices=SalesSourceStatus.choices, default=SalesSourceStatus.ACTIVE)
    credential_hash = models.CharField(max_length=64, blank=True, db_index=True)
    credential_hint = models.CharField(max_length=32, blank=True)
    allowed_schema_versions = models.JSONField(default=list, blank=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "product", "code"], name="uniq_sales_source_org_product_code"),
        ]

    def __str__(self) -> str:
        return f"{self.product.code}/{self.code} ({self.environment})"


class Sale(models.Model):
    """Актуальная нормализованная проекция внешней продажи (SPEC-HUB-0014 §3.1).

    Обновляется ТОЛЬКО application service на основании принятого SaleEvent. Прямой
    ORM-write из view/admin запрещён прикладным контрактом (§7.3).
    """

    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="sales")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="sales")
    sales_source = models.ForeignKey(SalesSource, on_delete=models.PROTECT, null=True, blank=True, related_name="sales")
    environment = models.CharField(max_length=16, choices=Environment.choices, default=Environment.PRODUCTION)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    external_sale_id = models.CharField(max_length=190, blank=True)
    external_customer_id = models.CharField(max_length=190, blank=True)
    contact = models.ForeignKey("conversations.Contact", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.SET_NULL, null=True, blank=True, related_name="sales")
    status = models.CharField(max_length=24, choices=SaleStatus.choices, default=SaleStatus.CONFIRMED)
    amount_minor = models.PositiveBigIntegerField(default=0)
    refunded_amount_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="RUB")
    occurred_at = models.DateTimeField(db_index=True)
    last_event_at = models.DateTimeField(null=True, blank=True)
    last_event = models.ForeignKey("sales.SaleEvent", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    attribution_method = models.CharField(max_length=24, choices=AttributionMethod.choices, default=AttributionMethod.NONE)
    attributed_actor_type = models.CharField(max_length=16, choices=ActorType.choices, blank=True)
    attributed_actor_id = models.CharField(max_length=64, blank=True)
    line_items_snapshot = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "environment", "occurred_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["sales_source", "external_sale_id"],
                condition=Q(sales_source__isnull=False) & ~Q(external_sale_id=""),
                name="uniq_sale_source_external",
            ),
            models.CheckConstraint(condition=Q(amount_minor__gte=0), name="sale_amount_non_negative"),
            models.CheckConstraint(
                condition=Q(refunded_amount_minor__gte=0) & Q(refunded_amount_minor__lte=F("amount_minor")),
                name="sale_refund_within_amount",
            ),
        ]

    @property
    def net_amount_minor(self) -> int:
        return self.amount_minor - self.refunded_amount_minor

    def __str__(self) -> str:
        return f"Sale#{self.id} {self.external_sale_id or '(manual)'} {self.status}"


class SaleEvent(models.Model):
    """Append-only журнал принятых событий продажи (SPEC-HUB-0014 §3.2).

    Каждое входящее или ручное изменение сначала сохраняется как неизменяемое
    событие, затем идемпотентно применяется к Sale. Физическое удаление и
    переписывание принятого события запрещено (ADR-HUB-0025 §4).
    """

    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="sale_events")
    sales_source = models.ForeignKey(SalesSource, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, null=True, blank=True, related_name="events")
    environment = models.CharField(max_length=16, choices=Environment.choices, default=Environment.PRODUCTION)
    source_type = models.CharField(max_length=16, choices=SourceType.choices)
    external_event_id = models.CharField(max_length=190, blank=True)
    event_type = models.CharField(max_length=32, choices=SaleEventType.choices)
    schema_version = models.PositiveIntegerField(default=1)
    occurred_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_user = models.ForeignKey("identity.HumanUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="sale_events")
    raw_payload = models.JSONField(default=dict, blank=True)
    processing_status = models.CharField(max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.RECEIVED)
    processing_error = models.TextField(blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["received_at", "id"]
        indexes = [models.Index(fields=["sale", "occurred_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["sales_source", "external_event_id"],
                condition=Q(sales_source__isnull=False) & ~Q(external_event_id=""),
                name="uniq_sale_event_source_external",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} evt#{self.id} ({self.processing_status})"


class AttributionToken(models.Model):
    """Непрозрачный токен связи коммерческого перехода из диалога (SPEC-HUB-0014 §3.3).

    В открытом URL не передаются UUID Hub. Хранится только hash. После разрешения
    не удаляется — остаётся частью аудита; может быть отозван до истечения срока.
    """

    token_hash = models.CharField(max_length=64, unique=True)
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="attribution_tokens")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="attribution_tokens")
    offer = models.ForeignKey("products.Offer", on_delete=models.SET_NULL, null=True, blank=True, related_name="attribution_tokens")
    contact = models.ForeignKey("conversations.Contact", on_delete=models.PROTECT, related_name="attribution_tokens")
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.PROTECT, related_name="attribution_tokens")
    channel = models.ForeignKey("channels.Channel", on_delete=models.PROTECT, null=True, blank=True, related_name="attribution_tokens")
    connection = models.ForeignKey("integrations.Integration", on_delete=models.SET_NULL, null=True, blank=True, related_name="attribution_tokens")
    actor_type = models.CharField(max_length=16, choices=ActorType.choices)
    actor_id = models.CharField(max_length=64, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    first_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "expires_at"])]

    def __str__(self) -> str:
        return f"AttributionToken#{self.id} {self.product_id}"


class ExternalCustomerIdentity(models.Model):
    """Связь пользователя внешнего продукта с Contact Hub (SPEC-HUB-0014 §3.4).

    Идентификация клиента != атрибуция продажи: повторная продажа принадлежит тому
    же клиенту, но не автоматически тому же оператору/диалогу. Автоматическое
    перепривязывание к другому Contact запрещено — только OWNER с причиной и аудитом.
    """

    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="external_customer_identities")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="external_customer_identities")
    environment = models.CharField(max_length=16, choices=Environment.choices, default=Environment.PRODUCTION)
    external_customer_id = models.CharField(max_length=190)
    contact = models.ForeignKey("conversations.Contact", on_delete=models.PROTECT, related_name="external_customer_identities")
    verification_method = models.CharField(max_length=32, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "External customer identities"
        constraints = [
            models.UniqueConstraint(
                fields=["product", "environment", "external_customer_id"],
                name="uniq_external_identity_product_env_customer",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product_id}:{self.external_customer_id} -> contact#{self.contact_id}"
