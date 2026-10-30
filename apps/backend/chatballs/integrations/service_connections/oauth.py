"""Вход через сервис по OAuth 2.0 (SPEC-0037 R-7; C4 rel-service-oauth).

* state одноразовый: в базе только его хэш, он привязан к сотруднику,
  организации и подключению (или черновику нового) и живёт ограниченное время;
* код обменивается с PKCE через защищённый транспорт, вне транзакции;
* обновление токена сериализовано захватом в записи настроек: обновляет
  один, остальные ждут его результата, сетевой запрос не держит транзакцию;
* отказ в обновлении означает, что доступ отозван или истёк: подключение
  получает «Нет доступа», путь восстановления — замена доступа.
"""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import uuid
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from chatballs.i18n import t
from chatballs.identity.instance_settings import public_base_url
from chatballs.identity.models import OrganizationMembership
from chatballs.identity.policy import has_capability_any_scope
from chatballs.integrations.adapters.auth import OutboundRequest
from chatballs.integrations.adapters.contracts import DEFAULT_LIMITS, AuthMethod
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.transport import TransportError
from chatballs.integrations.models import (
    Integration,
    IntegrationStatus,
    OAuthStateStatus,
    ServiceConnectionSettings,
    ServiceOAuthState,
)
from chatballs.integrations.service_connections.binding import dump_credentials, load_credentials
from chatballs.integrations.service_connections.errors import ServiceCheckFailed
from chatballs.integrations.service_connections.services import (
    OAUTH_EXTENSION,
    AccessInput,
    adapter_and_method,
    clean_values,
    save_new_connection,
    store_access,
)
from chatballs.integrations.tool_network import ToolAddressRejected
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.lookup import organization_by_public_id

CALLBACK_PATH = "/api/v1/service-oauth/callback/"
REFRESH_MARGIN = timedelta(seconds=60)
REFRESH_CLAIM = timedelta(seconds=60)
_WAIT_STEP_SECONDS = 0.5


class OAuthFailed(ServiceCheckFailed):
    """Вход или обновление токена не удались; ``code`` — причина."""


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _client(adapter_key: str) -> dict[str, str]:
    client = getattr(django_settings, "CHATBALLS_SERVICE_OAUTH_CLIENTS", {}).get(adapter_key)
    if not client or not client.get("client_id"):
        raise ValidationError({"authMethod": t("services.auth_method_unknown")})
    return client


def start_oauth(*, context: TenantContext, data: AccessInput, integration: Integration | None = None) -> tuple[ServiceOAuthState, str]:
    """Создать одноразовый state и адрес входа в сервис."""

    adapter, method = adapter_and_method(data.adapter_key, data.auth_method, listed_only=integration is None)
    if method.extension != OAUTH_EXTENSION:
        raise ValidationError({"authMethod": t("services.auth_method_unknown")})
    client = _client(adapter.key)
    settings, _secrets = clean_values(adapter, method, data.values)
    token = f"{context.organization.public_id}.{secrets.token_urlsafe(32)}"
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    redirect_uri = f"{public_base_url()}{CALLBACK_PATH}"
    with tenant_atomic(context):
        state = ServiceOAuthState.objects.create(
            organization_id=context.organization_id,
            state_hash=_hash(token),
            user=context.actor_user,
            integration=integration,
            adapter_key=adapter.key,
            adapter_version=adapter.contract_version,
            auth_method=method.key,
            draft={"name": data.name.strip(), "settings": settings},
            code_verifier=verifier,
            redirect_uri=redirect_uri,
            expires_at=timezone.now() + timedelta(seconds=django_settings.CHATBALLS_SERVICE_OAUTH_STATE_SECONDS),
        )
    query = {
        "response_type": "code",
        "client_id": client["client_id"],
        "redirect_uri": redirect_uri,
        "state": token,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if method.options.get("scopes"):
        query["scope"] = " ".join(method.options["scopes"])
    return state, f"{method.options['authorize_url']}?{urlencode(query)}"


def complete_oauth(*, user, token: str, code: str, error: str) -> ServiceOAuthState:
    """Принять возврат из сервиса. Чужой, повторный или просроченный state отклоняется."""

    organization = organization_by_public_id(_organization_part(token))
    if organization is None:
        raise OAuthFailed("oauth_invalid")
    with tenant_atomic(organization.id):
        state = ServiceOAuthState.objects.select_for_update().filter(state_hash=_hash(token)).first()
        if state is None or state.user_id != user.id or state.consumed_at is not None:
            raise OAuthFailed("oauth_invalid")
        state.consumed_at = timezone.now()
        if state.expires_at <= state.consumed_at:
            state.status, state.error_code = OAuthStateStatus.FAILED, "oauth_expired"
        elif error or not code:
            state.status, state.error_code = OAuthStateStatus.DENIED, "oauth_denied"
        state.save()
    if state.status != OAuthStateStatus.PENDING:
        return state
    # Права проверяются на момент возврата: за время входа их могли снять.
    with tenant_atomic(organization.id):
        membership = OrganizationMembership.objects.select_related("organization", "user").filter(
            organization=organization, user=user
        ).first()
        allowed = membership is not None and has_capability_any_scope(membership, "integrations.manage")
        if not allowed:
            ServiceOAuthState.objects.filter(pk=state.pk).update(status=OAuthStateStatus.FAILED, error_code="oauth_invalid")
    if not allowed:
        raise OAuthFailed("oauth_invalid")
    return _finish(context=TenantContext.for_membership(membership), state=state, code=code)


def _finish(*, context: TenantContext, state: ServiceOAuthState, code: str) -> ServiceOAuthState:
    adapter, method = adapter_and_method(state.adapter_key, state.auth_method, listed_only=state.integration_id is None)
    try:
        credentials, expires_at = _token_request(method, adapter.key, {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": state.redirect_uri,
            "code_verifier": state.code_verifier,
        })
        settings = state.draft.get("settings", {})
        if state.integration_id:
            integration = store_access(context=context, integration=state.integration, adapter=adapter, settings=settings,
                                       credentials=credentials, checked=True, expires_at=expires_at)
        else:
            integration = save_new_connection(context=context, adapter=adapter, method=method, name=state.draft.get("name", ""),
                                              settings=settings, credentials=credentials, checked=True, expires_at=expires_at)
    except (OAuthFailed, ValidationError) as failure:
        code_ = failure.code if isinstance(failure, OAuthFailed) else "rejected"
        with tenant_atomic(context):
            ServiceOAuthState.objects.filter(pk=state.pk).update(status=OAuthStateStatus.FAILED, error_code=code_)
        state.refresh_from_db()
        return state
    with tenant_atomic(context):
        ServiceOAuthState.objects.filter(pk=state.pk).update(status=OAuthStateStatus.COMPLETED, result=integration)
    state.refresh_from_db()
    return state


def fresh_credentials(*, tenant: TenantContext, integration: Integration, row: ServiceConnectionSettings, method: AuthMethod) -> dict[str, Any]:
    """Credentials для вызова; токен OAuth обновляется заранее и одним исполнителем."""

    credentials = load_credentials(row)
    if method.extension != OAUTH_EXTENSION:
        return credentials
    if row.credentials_expires_at is None or row.credentials_expires_at - REFRESH_MARGIN > timezone.now():
        return credentials
    claim = uuid.uuid4()
    now = timezone.now()
    with tenant_atomic(tenant):
        # Пока мы ждали транзакцию, другой исполнитель мог уже завершить
        # refresh. Старый снимок не должен повторно использовать refresh_token.
        current = ServiceConnectionSettings.objects.select_for_update().get(pk=row.pk)
        if current.credentials_expires_at is None or current.credentials_expires_at - REFRESH_MARGIN > timezone.now():
            return load_credentials(current)
        credentials = load_credentials(current)
        won = ServiceConnectionSettings.objects.filter(pk=row.pk).filter(
            _claim_free(now)
        ).update(refresh_claim=claim, refresh_claim_until=now + REFRESH_CLAIM)
    if not won:
        return _wait_for_refresh(tenant=tenant, row=row)
    try:
        fresh, expires_at = _token_request(method, row.adapter_key, {
            "grant_type": "refresh_token",
            "refresh_token": credentials.get("refresh_token", ""),
        })
    except OAuthFailed as error:
        _release(tenant, row, claim, lost=error.code, integration=integration)
        raise
    fresh.setdefault("refresh_token", credentials.get("refresh_token", ""))
    with tenant_atomic(tenant):
        # Записывает только владелец захвата: опоздавший результат не затрёт новый.
        saved = ServiceConnectionSettings.objects.filter(pk=row.pk, refresh_claim=claim).update(
            credentials=dump_credentials(fresh), credentials_expires_at=expires_at, refresh_claim=None, refresh_claim_until=None
        )
    return fresh if saved else _wait_for_refresh(tenant=tenant, row=row)


def _claim_free(now) -> Q:
    return Q(refresh_claim_until__isnull=True) | Q(refresh_claim_until__lt=now)


def _wait_for_refresh(*, tenant: TenantContext, row: ServiceConnectionSettings) -> dict[str, Any]:
    deadline = time.monotonic() + REFRESH_CLAIM.total_seconds()
    while time.monotonic() < deadline:
        time.sleep(_WAIT_STEP_SECONDS)
        with tenant_atomic(tenant):
            current = ServiceConnectionSettings.objects.select_related("integration").get(pk=row.pk)
        if current.refresh_claim is None:
            if current.credentials_expires_at is not None and current.credentials_expires_at <= timezone.now():
                raise OAuthFailed(current.integration.last_error_code or "temporary")
            return load_credentials(current)
    raise OAuthFailed("temporary")


def _release(tenant: TenantContext, row: ServiceConnectionSettings, claim: uuid.UUID, *, lost: str, integration: Integration) -> None:
    with tenant_atomic(tenant):
        released = ServiceConnectionSettings.objects.filter(pk=row.pk, refresh_claim=claim).update(refresh_claim=None, refresh_claim_until=None)
        if released and lost in ("access_revoked", "access_expired"):
            Integration.objects.filter(pk=integration.pk).update(
                status=IntegrationStatus.ERROR, last_error_code=lost, last_checked_at=timezone.now()
            )


def _token_request(method: AuthMethod, adapter_key: str, form: dict[str, str]) -> tuple[dict[str, Any], Any]:
    client = _client(adapter_key)
    body = urlencode({**form, "client_id": client["client_id"], "client_secret": client.get("client_secret", "")}).encode()
    request = OutboundRequest("POST", method.options["token_url"], {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}, body)
    transport = default_registry().extension("transport", "https@1").implementation
    try:
        response = transport.send(request, limits=DEFAULT_LIMITS)
    except (ToolAddressRejected, TransportError, OSError) as error:
        raise OAuthFailed("unreachable") from error
    try:
        payload = json.loads(response.body or b"{}")
    except ValueError as error:
        raise OAuthFailed("rejected") from error
    if response.status >= 400 or not payload.get("access_token"):
        revoked = payload.get("error") in ("invalid_grant", "unauthorized_client")
        raise OAuthFailed("access_revoked" if revoked else "rejected")
    expires_in = payload.get("expires_in")
    expires_at = timezone.now() + timedelta(seconds=int(expires_in)) if str(expires_in).isdigit() else None
    credentials = {key: payload[key] for key in ("access_token", "refresh_token", "token_type") if payload.get(key)}
    return credentials, expires_at


def _organization_part(token: str) -> str:
    head = token.split(".", 1)[0]
    try:
        return str(uuid.UUID(head))
    except ValueError:
        return "00000000-0000-0000-0000-000000000000"
