from django.db import models

# Коммерческий заказ (ADR-HUB-0018): каталог и факт продажи живут в Хабе,
# само исполнение (выдача доступа) — на стороне бэкенда продукта. Позиции
# хранят снимок offer/цены, чтобы запись не «плыла» при изменении каталога.


class PaymentStatus(models.TextChoices):
    PENDING = "PENDING", "Ожидает оплаты"
    PAID = "PAID", "Оплачен"
    CANCELLED = "CANCELLED", "Отменён"
    REFUNDED = "REFUNDED", "Возврат"


class FulfillmentStatus(models.TextChoices):
    NONE = "NONE", "Не требуется"
    PENDING = "PENDING", "В процессе"
    DELIVERED = "DELIVERED", "Исполнен"
    FAILED = "FAILED", "Ошибка"


class Order(models.Model):
    organization = models.ForeignKey("identity.Organization", on_delete=models.PROTECT, related_name="orders")
    contact = models.ForeignKey("conversations.Contact", on_delete=models.PROTECT, related_name="orders")
    conversation = models.ForeignKey("conversations.Conversation", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT, related_name="orders", null=True, blank=True)
    channel = models.ForeignKey("channels.Channel", on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")
    payment_status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    fulfillment_status = models.CharField(max_length=16, choices=FulfillmentStatus.choices, default=FulfillmentStatus.NONE)
    amount_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="RUB")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "payment_status"])]

    @property
    def code(self) -> str:
        return f"ORD-{self.id}"

    def __str__(self) -> str:
        return f"{self.code}/{self.payment_status}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    offer = models.ForeignKey("products.Offer", on_delete=models.PROTECT, related_name="order_items")
    price = models.ForeignKey("products.Price", on_delete=models.PROTECT, null=True, blank=True, related_name="order_items")
    title = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    amount_minor = models.PositiveBigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="RUB")

    def __str__(self) -> str:
        return f"{self.title} x{self.quantity}"
