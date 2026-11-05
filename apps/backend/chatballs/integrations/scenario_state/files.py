"""Операционные файлы сервисных операций (SPEC-0037 R-4, R-24).

Большие и бинарные данные операции не кладутся в JSON запуска, журнала или
outbox: они сохраняются штатным хранилищем организации, а дальше ходит ссылка
на файл. Срок жизни файла задаёт владелец данных шага; здесь только запись.
"""

from __future__ import annotations

import uuid
from pathlib import PurePath

from django.db import models

from chatballs.tenancy.models import TenantRelationModel


def service_file_upload_path(instance: ServiceFile, filename: str) -> str:
    organization = instance.integration.organization if instance.integration_id else instance.organization
    source = instance.integration_id if instance.integration_id else "native"
    return (
        f"organizations/{organization.public_id}/service-files/"
        f"{source}/{instance.public_id}{PurePath(filename).suffix}"
    )


class ServiceFile(TenantRelationModel):
    tenant_relation_fields = ("integration",)
    integration = models.ForeignKey(
        "integrations.Integration", on_delete=models.CASCADE, related_name="service_files", null=True, blank=True
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    file = models.FileField(upload_to=service_file_upload_path, max_length=512)
    name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=128)
    size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    # Existing/user-uploaded files retain their independent owner. A file
    # produced solely by execution follows its step's retention policy.
    independent_owner = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"service-file:{self.integration_id}/{self.public_id}"
