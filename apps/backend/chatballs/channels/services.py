"""Операции над каналом обработки (SPEC-HUB-0027 §6, §7)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from chatballs.channels import authorization
from chatballs.channels.models import Channel
from chatballs.identity.group_models import EmployeeGroup
from chatballs.integrations.models import Integration, IntegrationKind
from chatballs.tenancy.context import TenantContext

# SPEC §3.1: slug 1-64, входит в embed-URL web-виджета и после создания immutable.
CODE_MAX_LENGTH = 64
NAME_MAX_LENGTH = 255


class Unset:
    """Отличает «поле не передано» от «передан null»."""

    def __bool__(self) -> bool:
        return False


UNSET = Unset()


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
    group_id: Any = UNSET
    is_active: Any = UNSET
    policy: dict[str, bool] = field(default_factory=dict)


def _clean_name(raw: object) -> str:
    name = str(raw or "").strip()
    if not name:
        raise ValidationError({"name": "Название канала не может быть пустым"})
    if len(name) > NAME_MAX_LENGTH:
        raise ValidationError({"name": "Название канала длиннее 255 символов"})
    return name


def _group_for_channel(
    *, context: TenantContext, group_id: int | None
) -> EmployeeGroup | None:
    if group_id is None:
        return None
    try:
        return EmployeeGroup.objects.get(
            id=group_id,
            organization_id=context.organization_id,
        )
    except EmployeeGroup.DoesNotExist as error:
        raise ValidationError({"groupId": "Unknown group"}) from error


@transaction.atomic
def update_channel(
    *, context: TenantContext, channel: Channel, update: ChannelUpdate
) -> Channel:
    """Порядок обработки §6.5: блокировка, права по каждому полю, целевое
    состояние, инварианты, конфликты, одна транзакция.

    Инварианты проверяются по итоговому состоянию, а не по переданным полям:
    запрос, оставляющий канал в запрещённой комбинации, отклоняется целиком.
    """
    locked = Channel.objects.select_for_update().get(
        id=channel.id, organization_id=context.organization_id
    )

    if update.name is not UNSET:
        authorization.require_channel_manage(context)
    if update.group_id is not UNSET and update.group_id != locked.group_id:
        authorization.require_channel_manage(context)
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
    if update.group_id is not UNSET and update.group_id != locked.group_id:
        locked.group = _group_for_channel(context=context, group_id=update.group_id)
        changed.append("group")
    if update.is_active is not UNSET and update.is_active != locked.is_active:
        locked.is_active = bool(update.is_active)
        changed.append("is_active")
    for name, value in update.policy.items():
        if getattr(locked, name) != value:
            setattr(locked, name, value)
            changed.append(name)

    if changed:
        locked.save(update_fields=[*changed, "updated_at"])
    return locked


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
