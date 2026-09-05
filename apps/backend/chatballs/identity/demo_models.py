"""Реестр демо-данных организации.

Демо ставится в организацию установщика (мультиорг-переключателя нет —
решение владельца). Чтобы удаление было точным и не задело реальные данные,
каждая созданная сидом запись регистрируется в ``DemoRecord``; удаление идёт
по реестру в обратном порядке создания.
"""

from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models


class DemoDatasetStatus(models.TextChoices):
    INSTALLING = "INSTALLING", "Устанавливается"
    INSTALLED = "INSTALLED", "Установлены"
    REMOVING = "REMOVING", "Удаляются"
    FAILED = "FAILED", "Ошибка"


class DemoDataset(models.Model):
    """Состояние демо-набора организации: одна запись на организацию."""

    organization = models.OneToOneField(
        "identity.Organization", on_delete=models.CASCADE, related_name="demo_dataset"
    )
    status = models.CharField(
        max_length=16, choices=DemoDatasetStatus.choices, default=DemoDatasetStatus.INSTALLING
    )
    requested_by = models.ForeignKey(
        "identity.HumanUser", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    records_count = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "identity_demodataset"

    def __str__(self) -> str:
        return f"demo:{self.organization_id}:{self.status}"


class DemoRecord(models.Model):
    """Одна созданная сидом запись: модель + первичный ключ + порядок создания."""

    organization = models.ForeignKey(
        "identity.Organization", on_delete=models.CASCADE, related_name="+"
    )
    dataset = models.ForeignKey(DemoDataset, on_delete=models.CASCADE, related_name="records")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name="+")
    object_id = models.CharField(max_length=64)
    sequence = models.PositiveBigIntegerField()

    class Meta:
        db_table = "identity_demorecord"
        indexes = [models.Index(fields=["dataset", "sequence"])]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "content_type", "object_id"], name="identity_demorecord_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.content_type_id}:{self.object_id}"
