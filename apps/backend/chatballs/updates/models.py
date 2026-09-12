"""Состояние обновлений установки: одна строка на инсталляцию.

Не тенантная таблица: версия у установки одна на всех. Проверка релизов
живёт в воркере, установку запрашивает администратор установки, а выполняет
сервис updater вне приложения (ADR-CHATBALLS-0049).
"""

from __future__ import annotations

from django.db import models


class InstallStatus(models.TextChoices):
    IDLE = "IDLE", "Не запускалась"
    REQUESTED = "REQUESTED", "Запрошена"
    RUNNING = "RUNNING", "Идёт"
    DONE = "DONE", "Завершена"
    FAILED = "FAILED", "Ошибка"


class UpdateState(models.Model):
    SINGLETON_PK = 1

    # Что известно о последнем релизе на канале.
    latest_version = models.CharField(max_length=32, blank=True, default="")
    latest_name = models.CharField(max_length=128, blank=True, default="")
    latest_notes = models.TextField(blank=True, default="")
    latest_published_at = models.DateTimeField(null=True, blank=True)
    latest_compose_url = models.URLField(max_length=512, blank=True, default="")
    latest_page_url = models.URLField(max_length=512, blank=True, default="")
    checked_at = models.DateTimeField(null=True, blank=True)
    check_error = models.CharField(max_length=500, blank=True, default="")

    # Последняя запрошенная установка.
    install_version = models.CharField(max_length=32, blank=True, default="")
    install_status = models.CharField(
        max_length=12, choices=InstallStatus.choices, default=InstallStatus.IDLE
    )
    install_message = models.CharField(max_length=1000, blank=True, default="")
    install_requested_at = models.DateTimeField(null=True, blank=True)
    install_updated_at = models.DateTimeField(null=True, blank=True)
    # Кто нажал кнопку — для аудита и подписи в интерфейсе.
    install_requested_by = models.ForeignKey(
        "identity.HumanUser", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        verbose_name = "Обновления установки"

    def __str__(self) -> str:
        return f"updates:{self.latest_version or 'нет данных'}"

    def save(self, *args, **kwargs):
        self.pk = self.SINGLETON_PK
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> UpdateState:
        obj, _ = cls.objects.get_or_create(pk=cls.SINGLETON_PK)
        return obj
