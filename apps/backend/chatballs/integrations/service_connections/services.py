"""Жизненный цикл сервисного подключения (SPEC-0037 R-1, R-7; ADR-0038 п.2).

Подключение создаётся, только когда доступ проверен (адаптер без проверки
сохраняется «Не проверено»). Сетевая проверка идёт вне транзакции, запись —
короткой транзакцией в контексте организации. Несколько подключений одного
адаптера различаются названием; Channel и AIAgent не нужны.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from chatballs.i18n import t
from chatballs.integrations.adapters.auth import split_values
from chatballs.integrations.adapters.contracts import AdapterDescriptor, AuthMethod
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import TypeSpec, validate_value
from chatballs.integrations.deletion import delete_integration
from chatballs.integrations.models import (
    Integration,
    IntegrationKind,
    IntegrationProvider,
    IntegrationStatus,
    ServiceConnectionSettings,
)
from chatballs.integrations.service_connections.binding import (
    ServiceUnavailable,
    dump_credentials,
    resolve,
)
from chatballs.integrations.service_connections.checks import run_check
from chatballs.integrations.service_connections.errors import ServiceCheckFailed
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic

OAUTH_EXTENSION = "oauth2@1"


@dataclass(frozen=True)
class AccessInput:
    adapter_key: str
    auth_method: str
    values: dict[str, Any] = field(default_factory=dict)
    name: str = ""


def adapter_and_method(adapter_key: str, auth_method: str, *, listed_only: bool = True) -> tuple[AdapterDescriptor, AuthMethod]:
    adapter = default_registry().adapter(adapter_key)
    if adapter is None or (listed_only and not adapter.listed):
        raise ValidationError({"adapter": t("services.adapter_unknown")})
    method = adapter.auth_method(auth_method)
    if method is None:
        raise ValidationError({"authMethod": t("services.auth_method_unknown")})
    return adapter, method


def clean_values(adapter: AdapterDescriptor, method: AuthMethod, values: dict[str, Any]) -> tuple[dict, dict]:
    """Настройки и секреты из введённого; ошибки — по полям формы."""

    fields = TypeSpec("object", properties=method.fields.properties + adapter.settings.properties)
    known = {name: values[name] for name, _spec in fields.properties if name in values}
    errors: dict[str, list[str]] = {}
    for issue in validate_value(fields, {k: v.strip() if isinstance(v, str) else v for k, v in known.items()}):
        name = issue.path.split(".")[0].split("[")[0]
        spec = fields.field(name)
        if issue.code == "required":
            message = t("services.field_required")
        elif issue.code == "pattern" and spec is not None and spec.pattern_error_key:
            message = t(spec.pattern_error_key)
        else:
            message = t("services.field_invalid")
        errors.setdefault(name, [message])
    if errors:
        raise ValidationError(errors)
    return split_values(fields, known)


def _clean_name(context: TenantContext, name: str, *, exclude_id: int | None = None) -> str:
    name = name.strip()
    if not name:
        raise ValidationError({"name": t("services.name_required")})
    taken = Integration.objects.filter(
        organization_id=context.organization_id, provider=IntegrationProvider.ADAPTER, name=name
    ).exclude(id=exclude_id)
    if taken.exists():
        raise ValidationError({"name": t("services.name_taken")})
    return name


def create_connection(*, context: TenantContext, data: AccessInput) -> Integration:
    adapter, method = adapter_and_method(data.adapter_key, data.auth_method)
    if method.extension == OAUTH_EXTENSION:
        raise ValidationError({"authMethod": t("services.auth_method_unknown")})
    with tenant_atomic(context):
        name = _clean_name(context, data.name)
    settings, credentials = clean_values(adapter, method, data.values)
    draft = Integration(organization_id=context.organization_id, kind=IntegrationKind.SERVICE,
                        provider=IntegrationProvider.ADAPTER, name=name)
    checked = method.check is not None
    if checked:
        run_check(tenant=None, integration=draft, adapter=adapter, method=method, settings=settings, credentials=credentials)
    return save_new_connection(
        context=context, adapter=adapter, method=method, name=name, settings=settings, credentials=credentials, checked=checked
    )


def save_new_connection(
    *, context: TenantContext, adapter: AdapterDescriptor, method: AuthMethod, name: str,
    settings: dict, credentials: dict, checked: bool, expires_at=None,
) -> Integration:
    with tenant_atomic(context):
        integration = Integration.objects.create(
            organization_id=context.organization_id,
            kind=IntegrationKind.SERVICE,
            provider=IntegrationProvider.ADAPTER,
            name=_clean_name(context, name),
            status=IntegrationStatus.OK if checked else IntegrationStatus.UNCHECKED,
            last_checked_at=timezone.now() if checked else None,
        )
        ServiceConnectionSettings.objects.create(
            organization_id=context.organization_id,
            integration=integration,
            adapter_key=adapter.key,
            adapter_version=adapter.contract_version,
            auth_method=method.key,
            settings=settings,
            credentials=dump_credentials(credentials),
            credentials_expires_at=expires_at,
        )
    return integration


def replace_access(*, context: TenantContext, integration: Integration, values: dict[str, Any]) -> Integration:
    """Новый доступ к тому же подключению: настройки сценариев сохраняются."""

    row = integration.service_settings
    adapter, method = adapter_and_method(row.adapter_key, row.auth_method, listed_only=False)
    if method.extension == OAUTH_EXTENSION:
        raise ValidationError({"authMethod": t("services.auth_method_unknown")})
    settings, credentials = clean_values(adapter, method, values)
    checked = method.check is not None
    if checked:
        run_check(tenant=context, integration=integration, adapter=adapter, method=method, settings=settings, credentials=credentials)
    return store_access(context=context, integration=integration, adapter=adapter, settings=settings,
                        credentials=credentials, checked=checked)


def store_access(*, context: TenantContext, integration: Integration, adapter: AdapterDescriptor,
                 settings: dict, credentials: dict, checked: bool, expires_at=None) -> Integration:
    with tenant_atomic(context):
        row = ServiceConnectionSettings.objects.select_for_update().get(integration=integration)
        row.settings, row.credentials = settings, dump_credentials(credentials)
        row.adapter_version = adapter.contract_version
        row.credentials_expires_at = expires_at
        row.refresh_claim = row.refresh_claim_until = None
        row.save()
        _set_status(integration, IntegrationStatus.OK if checked else IntegrationStatus.UNCHECKED, checked=checked)
    return integration


def check_connection(*, context: TenantContext, integration: Integration, inputs: dict[str, Any] | None = None) -> Integration:
    """Проверить сохранённый доступ; ошибка проверки записывается в состояние."""

    try:
        row, adapter, method = resolve(integration)
    except ServiceUnavailable as error:
        raise ServiceCheckFailed(error.code) from error
    from chatballs.integrations.service_connections.oauth import fresh_credentials

    try:
        credentials = fresh_credentials(tenant=context, integration=integration, row=row, method=method)
        run_check(tenant=context, integration=integration, adapter=adapter, method=method,
                  settings=row.settings, credentials=credentials, inputs=inputs)
    except ServiceCheckFailed as error:
        if error.code != "arguments":
            with tenant_atomic(context):
                _set_status(integration, IntegrationStatus.ERROR, checked=True, error_code=error.code)
        raise
    with tenant_atomic(context):
        _set_status(integration, IntegrationStatus.OK, checked=True)
    return integration


def rename_connection(*, context: TenantContext, integration: Integration, name: str) -> Integration:
    with tenant_atomic(context):
        integration.name = _clean_name(context, name, exclude_id=integration.id)
        integration.save(update_fields=["name", "updated_at"])
    return integration


def set_active(*, context: TenantContext, integration: Integration, active: bool) -> Integration:
    """Пауза: новые операции подключения не выполняются, доступ и настройки сохранены."""

    with tenant_atomic(context):
        integration.is_active = active
        integration.save(update_fields=["is_active", "updated_at"])
    return integration


def delete_connection(*, context: TenantContext, integration: Integration) -> None:
    """Удалить подключение; данные в самом сервисе не меняются."""

    with tenant_atomic(context):
        delete_integration(context=context, integration=integration)


def _set_status(integration: Integration, status: str, *, checked: bool, error_code: str = "") -> None:
    integration.status = status
    integration.last_error_code = error_code
    integration.last_error = ""
    if checked:
        integration.last_checked_at = timezone.now()
    integration.save(update_fields=["status", "last_error_code", "last_error", "last_checked_at", "updated_at"])
