"""Операции над каналом обработки (SPEC-HUB-0027 §6, §7)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from hub_platform.ai.knowledge_conflicts import require_channel_department_compatible
from hub_platform.channels import authorization
from hub_platform.channels.models import Channel
from hub_platform.channels.policy import ChannelPolicy, require_valid_policy
from hub_platform.identity.models import Department, DepartmentStatus
from hub_platform.integrations.models import Integration, IntegrationKind
from hub_platform.products.models import Product
from hub_platform.tenancy.context import TenantContext

# SPEC §3.1: slug 1-64, входит в embed-URL web-виджета и после создания immutable.
CODE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CODE_MAX_LENGTH = 64
NAME_MAX_LENGTH = 255


class Unset:
    """Отличает «поле не передано» от «передан null»."""

    def __bool__(self) -> bool:
        return False


UNSET = Unset()


class ChannelCodeConflict(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"Канал с кодом {code} уже существует")


class ChannelHasReferences(Exception):
    """§7.2. SET_NULL и CASCADE не считаются разрешением на удаление."""

    def __init__(self, blockers: list[dict[str, Any]]) -> None:
        self.blockers = blockers
        super().__init__("Канал нельзя удалить: есть связанные записи")

    def payload(self) -> dict[str, Any]:
        return {"detail": str(self), "blockers": self.blockers}


class ConnectionAlreadyBound(Exception):
    """Подключение принадлежит ровно одному каналу (ADR-HUB-0019)."""

    def __init__(self, *, integration: Integration) -> None:
        self.integration = integration
        super().__init__(
            "Подключение уже привязано к другому каналу: перенос требует force"
        )

    def payload(self) -> dict[str, Any]:
        return {
            "detail": str(self),
            "code": "connection_already_bound",
            "currentChannel": {
                "id": self.integration.channel_id,
                "name": self.integration.channel.name,
            },
        }


@dataclass(frozen=True)
class ChannelUpdate:
    """Частичное изменение: UNSET — поле не передано (SPEC §6.5)."""

    name: Any = UNSET
    department_id: Any = UNSET
    product_id: Any = UNSET
    is_active: Any = UNSET
    policy: dict[str, bool] = field(default_factory=dict)


def _clean_code(raw: object) -> str:
    code = str(raw or "").strip()
    if not code or len(code) > CODE_MAX_LENGTH or not CODE_PATTERN.match(code):
        raise ValidationError(
            {"code": "Код канала: 1-64 символа, латиница в нижнем регистре, цифры и дефис"}
        )
    return code


def _clean_name(raw: object) -> str:
    name = str(raw or "").strip()
    if not name:
        raise ValidationError({"name": "Название канала не может быть пустым"})
    if len(name) > NAME_MAX_LENGTH:
        raise ValidationError({"name": "Название канала длиннее 255 символов"})
    return name


def _department_for_channel(
    *, context: TenantContext, department_id: int | None
) -> Department | None:
    if department_id is None:
        return None
    try:
        return Department.objects.get(
            id=department_id,
            organization_id=context.organization_id,
            status=DepartmentStatus.ACTIVE,
        )
    except Department.DoesNotExist as error:
        raise ValidationError({"departmentId": "Unknown or disabled department"}) from error


def _product_for_channel(
    *, context: TenantContext, product_id: int | None
) -> Product | None:
    if product_id is None:
        return None
    try:
        return Product.objects.get(
            id=product_id, organization_id=context.organization_id
        )
    except Product.DoesNotExist as error:
        raise ValidationError({"productId": "Unknown product"}) from error


@transaction.atomic
def create_channel(
    *,
    context: TenantContext,
    code: object,
    name: object,
    department_id: int | None,
    product_id: int | None,
    policy: ChannelPolicy,
    connection_ids: list[int] | None = None,
) -> Channel:
    authorization.require_organization_manage(context, operation="Создание канала")
    clean_code = _clean_code(code)
    clean_name = _clean_name(name)
    department = _department_for_channel(context=context, department_id=department_id)
    product = _product_for_channel(context=context, product_id=product_id)
    # Инварианты проверяются до записи: частичное применение запрещено (§3.2).
    require_valid_policy(policy=policy, has_product=product is not None)

    if Channel.objects.filter(
        organization_id=context.organization_id, code=clean_code
    ).exists():
        raise ChannelCodeConflict(clean_code)

    channel = Channel.objects.create(
        organization_id=context.organization_id,
        code=clean_code,
        name=clean_name,
        department=department,
        product=product,
        **policy.as_model_fields(),
    )
    for integration_id in connection_ids or []:
        bind_connection(context=context, channel=channel, integration_id=integration_id)
    return channel


@transaction.atomic
def update_channel(
    *, context: TenantContext, channel: Channel, update: ChannelUpdate
) -> Channel:
    """Порядок обработки §6.5: блокировка, права по каждому полю, целевое
    состояние, инварианты, конфликты, одна транзакция.

    Инварианты проверяются по итоговому состоянию, а не по переданным полям:
    выключить продукт и коммерческие флаги можно одним запросом, а вот запрос,
    оставляющий канал в запрещённой комбинации, отклоняется целиком.
    """
    locked = Channel.objects.select_for_update().get(
        id=channel.id, organization_id=context.organization_id
    )

    if update.name is not UNSET:
        authorization.require_channel_manage(
            context, department_id=locked.department_id
        )
    if update.department_id is not UNSET and update.department_id != locked.department_id:
        authorization.require_department_change(
            context,
            current_department_id=locked.department_id,
            target_department_id=update.department_id,
        )
    if update.product_id is not UNSET and update.product_id != locked.product_id:
        authorization.require_organization_manage(
            context, operation="Изменение продукта канала"
        )
    if update.is_active is not UNSET and update.is_active != locked.is_active:
        authorization.require_organization_manage(
            context, operation="Изменение статуса канала"
        )
    if update.policy:
        authorization.require_organization_manage(
            context, operation="Изменение политики канала"
        )

    changed: list[str] = []
    if update.name is not UNSET:
        clean_name = _clean_name(update.name)
        if clean_name != locked.name:
            locked.name = clean_name
            changed.append("name")
    if update.department_id is not UNSET and update.department_id != locked.department_id:
        department = _department_for_channel(
            context=context, department_id=update.department_id
        )
        require_channel_department_compatible(
            channel=locked, department_id=update.department_id
        )
        locked.department = department
        changed.append("department")
    if update.product_id is not UNSET and update.product_id != locked.product_id:
        product = _product_for_channel(context=context, product_id=update.product_id)
        locked.product = product
        changed.append("product")
    if update.is_active is not UNSET and update.is_active != locked.is_active:
        locked.is_active = bool(update.is_active)
        changed.append("is_active")
    for name, value in update.policy.items():
        if getattr(locked, name) != value:
            setattr(locked, name, value)
            changed.append(name)

    # Инварианты по целевому состоянию — до записи: нарушение отклоняет запрос
    # целиком, частичного применения не остаётся даже в памяти (§3.2, §6.5).
    require_valid_policy(
        policy=ChannelPolicy.from_channel(locked),
        has_product=locked.product_id is not None,
    )

    if changed:
        locked.save(update_fields=[*changed, "updated_at"])
    return locked


def deletion_blockers(channel: Channel) -> list[dict[str, Any]]:
    """§7.2. Каскадное удаление агента запрещено, поэтому SET_NULL и CASCADE
    тоже блокируют."""
    counts = (
        ("conversations", channel.conversations.count()),
        ("connections", channel.connections.count()),
        ("supportContracts", channel.allowed_support_contracts.count()),
        ("agent", 1 if hasattr(channel, "ai_agent") else 0),
        ("llmInvocations", channel.ai_invocations.count()),
    )
    return [{"type": name, "count": count} for name, count in counts if count]


@transaction.atomic
def delete_channel(*, context: TenantContext, channel: Channel) -> None:
    authorization.require_organization_manage(context, operation="Удаление канала")
    blockers = deletion_blockers(channel)
    if blockers:
        raise ChannelHasReferences(blockers)
    channel.delete()


def _messenger_integration(*, context: TenantContext, integration_id: int) -> Integration:
    try:
        integration = Integration.objects.select_related("channel").get(
            id=integration_id, organization_id=context.organization_id
        )
    except Integration.DoesNotExist as error:
        raise ValidationError({"integrationId": "Подключение не найдено"}) from error
    if integration.kind != IntegrationKind.MESSENGER:
        raise ValidationError(
            {"integrationId": "LLM-провайдер не является подключением канала"}
        )
    return integration


@transaction.atomic
def bind_connection(
    *,
    context: TenantContext,
    channel: Channel,
    integration_id: int,
    force: bool = False,
) -> tuple[Integration, int | None]:
    """Привязка подключения. Возвращает интеграцию и прежний канал переноса."""
    authorization.require_connections_manage(context)
    if not channel.is_active:
        raise ValidationError(
            {"channelId": "Нельзя привязать подключение к архивному каналу"}
        )
    integration = _messenger_integration(context=context, integration_id=integration_id)
    previous_channel_id = integration.channel_id
    if previous_channel_id == channel.id:
        return integration, None
    if previous_channel_id is not None and not force:
        raise ConnectionAlreadyBound(integration=integration)
    integration.channel = channel
    integration.save(update_fields=["channel", "updated_at"])
    return integration, previous_channel_id


@transaction.atomic
def unbind_connection(
    *, context: TenantContext, channel: Channel, integration_id: int
) -> Integration:
    authorization.require_connections_manage(context)
    integration = _messenger_integration(context=context, integration_id=integration_id)
    if integration.channel_id != channel.id:
        raise ValidationError({"integrationId": "Подключение не привязано к каналу"})
    # Диалоги не затрагиваются: Conversation.connection объявлен PROTECT.
    integration.channel = None
    integration.save(update_fields=["channel", "updated_at"])
    return integration
