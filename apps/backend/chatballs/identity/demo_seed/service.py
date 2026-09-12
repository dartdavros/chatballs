"""Установка и удаление демо-данных организации.

Запрос (из мастера первого запуска или из «Настроек») фиксирует состояние
``DemoDataset`` и ставит outbox-событие; работу выполняет worker
(``identity.event_handlers``), чтобы HTTP-запрос не ждал минуты индексации
знаний и раскладки файлов. Карточка в настройках опрашивает ``demo_status``.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from chatballs.events.services import DomainEvent, enqueue_event
from chatballs.identity.audit import record_audit_event
from chatballs.identity.avatars import user_avatar_url_in
from chatballs.identity.demo_models import DemoDataset, DemoDatasetStatus
from chatballs.identity.demo_seed.orchestrator import run_demo_seed
from chatballs.identity.demo_seed.registry import recording, remove_records
from chatballs.identity.models import HumanUser, Organization
from chatballs.tenancy.context import TenantContext

logger = logging.getLogger(__name__)

from chatballs.identity.event_handlers import (  # noqa: E402
    DEMO_INSTALL_REQUESTED,
    DEMO_REMOVE_REQUESTED,
)


class DemoBusy(ValidationError):
    """Установка или удаление уже идут."""


def showcase_accounts(organization_id: int) -> list[dict[str, object]]:
    """Учётки для входа «посмотреть глазами сотрудника»: админ и по одному
    сотруднику из разных групп. Пароль общий и намеренно публичный — это демо."""
    from chatballs.i18n import customer_language
    from chatballs.identity.demo_seed import manifest

    organization = Organization.objects.filter(id=organization_id).first()
    data = manifest.load("organization", customer_language(organization))
    by_key = {item["key"]: item for item in data["accounts"]}
    groups = {item["key"]: item["name"] for item in data.get("groups", [])}
    keys = data.get("showcaseAccounts", [])
    emails = [by_key[key]["email"] for key in keys]
    users = {user.email: user for user in HumanUser.objects.filter(email__in=emails)}
    accounts = []
    for key in keys:
        item = by_key[key]
        user = users.get(item["email"])
        accounts.append(
            {
                "fullName": item["fullName"],
                "email": item["email"],
                "password": data["demoPassword"],
                "role": item["role"],
                "positionTitle": item.get("positionTitle", ""),
                "groups": [groups[g] for g in item.get("groups", []) if g in groups],
                # Фото сотрудника — кадр N7 показывает его в строке учётки.
                "avatarUrl": user_avatar_url_in(user, organization_id) if user else None,
            }
        )
    return accounts


def demo_status(organization: Organization) -> dict[str, object]:
    dataset = DemoDataset.objects.filter(organization=organization).first()
    if dataset is None:
        return {
            "status": "ABSENT",
            "recordsCount": 0,
            "error": "",
            "startedAt": None,
            "finishedAt": None,
            "accounts": [],
        }
    installed = dataset.status == DemoDatasetStatus.INSTALLED
    return {
        "status": dataset.status,
        "recordsCount": dataset.records_count,
        "error": dataset.error,
        "startedAt": dataset.started_at.isoformat(),
        "finishedAt": dataset.finished_at.isoformat() if dataset.finished_at else None,
        "accounts": showcase_accounts(organization.id) if installed else [],
    }


def _busy(dataset: DemoDataset | None) -> bool:
    return dataset is not None and dataset.status in (
        DemoDatasetStatus.INSTALLING,
        DemoDatasetStatus.REMOVING,
    )


def request_install(*, context: TenantContext, actor: HumanUser | None) -> DemoDataset:
    """Ставит установку в очередь. Повторный запрос при установленном наборе —
    ошибка: сначала удаление."""
    with transaction.atomic():
        dataset = (
            DemoDataset.objects.select_for_update()
            .filter(organization_id=context.organization_id)
            .first()
        )
        if _busy(dataset):
            raise DemoBusy({"demo": "Демо-данные сейчас устанавливаются или удаляются"})
        if dataset is not None and dataset.status == DemoDatasetStatus.INSTALLED:
            raise ValidationError({"demo": "Демо-данные уже установлены"})
        if dataset is None:
            dataset = DemoDataset(organization_id=context.organization_id)
        dataset.status = DemoDatasetStatus.INSTALLING
        dataset.requested_by = actor
        dataset.error = ""
        dataset.finished_at = None
        dataset.started_at = timezone.now()
        dataset.save()
        record_audit_event(
            organization=context.organization,
            actor=actor,
            action="demo.install_requested",
            object_type="DemoDataset",
            object_id=str(dataset.id),
        )
        enqueue_event(
            DomainEvent(
                aggregate_type="DemoDataset",
                aggregate_id=str(dataset.id),
                event_type=DEMO_INSTALL_REQUESTED,
                payload={"datasetId": dataset.id},
                tenant_context=context,
            )
        )
    return dataset


def request_remove(*, context: TenantContext, actor: HumanUser | None) -> DemoDataset:
    with transaction.atomic():
        dataset = (
            DemoDataset.objects.select_for_update()
            .filter(organization_id=context.organization_id)
            .first()
        )
        if dataset is None:
            raise ValidationError({"demo": "Демо-данные не установлены"})
        if _busy(dataset):
            raise DemoBusy({"demo": "Демо-данные сейчас устанавливаются или удаляются"})
        dataset.status = DemoDatasetStatus.REMOVING
        dataset.requested_by = actor
        dataset.error = ""
        dataset.finished_at = None
        dataset.save(update_fields=["status", "requested_by", "error", "finished_at"])
        record_audit_event(
            organization=context.organization,
            actor=actor,
            action="demo.remove_requested",
            object_type="DemoDataset",
            object_id=str(dataset.id),
        )
        enqueue_event(
            DomainEvent(
                aggregate_type="DemoDataset",
                aggregate_id=str(dataset.id),
                event_type=DEMO_REMOVE_REQUESTED,
                payload={"datasetId": dataset.id},
                tenant_context=context,
            )
        )
    return dataset


def install(*, context: TenantContext, dataset: DemoDataset) -> DemoDataset:
    """Выполняет сид под записью в реестр. Вызывается внутри tenant_atomic."""
    try:
        # Savepoint: при сбое откатываются и данные, и их записи в реестре —
        # набор либо полный, либо отсутствует.
        with transaction.atomic(), recording(dataset) as recorder:
            run_demo_seed(context, recorder=recorder)
        dataset.records_count = dataset.records.count()
        dataset.status = DemoDatasetStatus.INSTALLED
        dataset.error = ""
    except Exception as error:  # noqa: BLE001 — статус ошибки должен дойти до UI
        logger.exception("Demo install failed for organization %s", context.organization_id)
        dataset.records_count = 0
        dataset.status = DemoDatasetStatus.FAILED
        dataset.error = str(error)[:2000]
    dataset.finished_at = timezone.now()
    dataset.save(update_fields=["records_count", "status", "error", "finished_at"])
    record_audit_event(
        organization=context.organization,
        actor=dataset.requested_by,
        action="demo.installed" if dataset.status == DemoDatasetStatus.INSTALLED else "demo.install_failed",
        object_type="DemoDataset",
        object_id=str(dataset.id),
        payload={"recordsCount": dataset.records_count},
    )
    return dataset


def remove(*, context: TenantContext, dataset: DemoDataset) -> None:
    """Удаляет записи по реестру и сам дата-сет. Вызывается внутри tenant_atomic."""
    removed = remove_records(dataset)
    record_audit_event(
        organization=context.organization,
        actor=dataset.requested_by,
        action="demo.removed",
        object_type="DemoDataset",
        object_id=str(dataset.id),
        payload={"recordsCount": removed},
    )
    dataset.delete()
