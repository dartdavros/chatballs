"""Настройки сервисного подключения и одноразовый OAuth state (SPEC-0037 R-1, R-7).

Подключение сервиса — обычный ``Integration`` вида SERVICE с общим provider
ADAPTER. Чем именно оно является, говорит отдельная запись настроек: ключ
адаптера, версия контракта, способ доступа, несекретные настройки и
зашифрованные credentials. Новому сервису не нужен свой enum.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from chatballs.identity.crypto import EncryptedCharField
from chatballs.tenancy.models import TenantRelationModel

# Сколько символов credentials помещается в запись: JSON нескольких токенов,
# сертификата и ключа клиента.
CREDENTIALS_MAX_LENGTH = 32768


class ServiceConnectionSettings(TenantRelationModel):
    tenant_relation_fields = ("integration",)
    integration = models.OneToOneField(
        "integrations.Integration", on_delete=models.CASCADE, related_name="service_settings"
    )
    adapter_key = models.CharField(max_length=64)
    # Версия контракта адаптера, с которой подключение сохранено: новая версия
    # пакета не переинтерпретирует его молча (R-18).
    adapter_version = models.PositiveIntegerField()
    auth_method = models.CharField(max_length=64)
    settings = models.JSONField(default=dict, blank=True)
    # JSON секретов способа доступа (Fernet). Наружу не отдаётся никогда.
    credentials = EncryptedCharField(max_length=CREDENTIALS_MAX_LENGTH, blank=True)
    credentials_expires_at = models.DateTimeField(null=True, blank=True)
    # Захват обновления токена: один обновляющий на подключение, без
    # транзакции на время сетевого запроса.
    refresh_claim = models.UUIDField(null=True, blank=True)
    refresh_claim_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"service:{self.adapter_key}@{self.adapter_version}/{self.integration_id}"


class OAuthStateStatus(models.TextChoices):
    PENDING = "PENDING", "Ожидает разрешения"
    COMPLETED = "COMPLETED", "Подключено"
    DENIED = "DENIED", "Доступ не предоставлен"
    FAILED = "FAILED", "Ошибка"


class ServiceOAuthState(TenantRelationModel):
    """Одноразовый state входа через сервис.

    Привязан к сотруднику, организации и подключению (при восстановлении
    доступа) или к черновику нового подключения. В базе лежит только хэш
    state: сам он есть лишь в адресе, по которому ушёл пользователь.
    """

    tenant_relation_fields = ("integration", "result")
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    state_hash = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    integration = models.ForeignKey(
        "integrations.Integration", on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    adapter_key = models.CharField(max_length=64)
    adapter_version = models.PositiveIntegerField()
    auth_method = models.CharField(max_length=64)
    # Название и несекретные настройки нового подключения.
    draft = models.JSONField(default=dict, blank=True)
    code_verifier = EncryptedCharField(max_length=128, blank=True)
    redirect_uri = models.CharField(max_length=512)
    status = models.CharField(max_length=16, choices=OAuthStateStatus.choices, default=OAuthStateStatus.PENDING)
    error_code = models.CharField(max_length=32, blank=True)
    result = models.ForeignKey(
        "integrations.Integration", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"oauth-state:{self.public_id}"
