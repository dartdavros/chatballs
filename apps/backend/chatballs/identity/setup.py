"""Мастер первого запуска (SPEC-CHATBALLS-0031, open source: «развернуть за минуту»).

Пока в инстансе нет ни одной организации, публичный эндпоинт /api/v1/setup/
принимает одну форму: название организации, имя, e-mail и пароль владельца.
Никаких параметров в .env и CLI: всё задаёт человек в браузере. После
создания владельца мастер закрывается навсегда (409).

Запись идёт на соединении ``platform`` — единственной runtime-роли с правом
создавать организации (SPEC-HUB-0021 §10); RLS-контекст и транзакция живут
на том же соединении.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connections, transaction
from django.utils.text import slugify

from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.i18n import t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.instance_settings import remember_public_host
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.routing import use_database

ORGANIZATION_NAME_MAX_LENGTH = 255
FULL_NAME_MAX_LENGTH = 255

# Алиас соединения для операций уровня инстанса. В тестах оба алиаса —
# зеркала одной тестовой БД под ролью-владельцем кластера.
INSTANCE_DB_ALIAS = "default" if settings.TESTING else "platform"


class SetupAlreadyCompleted(Exception):
    """Организация уже есть — мастер закрыт."""


@dataclass(frozen=True)
class SetupInput:
    organization_name: str
    full_name: str
    email: str
    password: str
    install_demo: bool = False


@dataclass(frozen=True)
class SetupResult:
    organization: Organization
    owner: HumanUser


def instance_needs_setup() -> bool:
    """Мастер нужен, пока не создана ни одна организация.

    Организации видны роли app целиком (RLS SELECT USING true), поэтому
    проверка не требует tenant-контекста.
    """
    with use_database(INSTANCE_DB_ALIAS):
        return not Organization.objects.exists()


def _clean(data: SetupInput) -> SetupInput:
    errors: dict[str, str] = {}
    organization_name = data.organization_name.strip()
    if not organization_name:
        errors["organizationName"] = t("admin.organization_name_required")
    elif len(organization_name) > ORGANIZATION_NAME_MAX_LENGTH:
        errors["organizationName"] = "Название длиннее 255 символов"
    full_name = " ".join(data.full_name.split())
    if not full_name:
        errors["fullName"] = "Укажите ваше имя"
    elif len(full_name) > FULL_NAME_MAX_LENGTH:
        errors["fullName"] = "Имя длиннее 255 символов"
    email = data.email.strip()
    try:
        validate_email(email)
    except ValidationError:
        errors["email"] = "Укажите корректный e-mail"
    if errors:
        raise ValidationError(errors)
    return SetupInput(
        organization_name=organization_name,
        full_name=full_name,
        email=HumanUser.objects.normalize_email(email).lower(),
        password=data.password,
        install_demo=data.install_demo,
    )


def _unique_slug(name: str) -> str:
    base = slugify(name)[:40].strip("-") or "organization"
    candidate = base
    suffix = 2
    while Organization.objects.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def complete_setup(
    data: SetupInput, public_host: str = "", public_scheme: str = "http"
) -> SetupResult:
    clean = _clean(data)
    with use_database(INSTANCE_DB_ALIAS), transaction.atomic(using=INSTANCE_DB_ALIAS):
        # Адрес, на котором человек прошёл мастер, и есть публичный адрес
        # установки: другого источника у коробки нет.
        if public_host:
            remember_public_host(public_host, public_scheme)
        # Блокировка от гонки двух вкладок: второй запрос дождётся первого и
        # увидит созданную организацию.
        with connections[INSTANCE_DB_ALIAS].cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('chatballs.instance_setup'))")
        if Organization.objects.exists():
            raise SetupAlreadyCompleted()

        # Пароль проверяется против атрибутов будущего пользователя (схожесть
        # с e-mail и именем) до записи чего-либо.
        probe = HumanUser(email=clean.email, full_name=clean.full_name)
        validate_password(clean.password, user=probe)

        organization = Organization.objects.create(
            name=clean.organization_name,
            slug=_unique_slug(clean.organization_name),
            status=OrganizationStatus.ACTIVE,
        )
        with tenant_atomic(organization.id, using=INSTANCE_DB_ALIAS):
            ensure_uncategorized_category(organization)
            owner = HumanUser.objects.create_user(
                email=clean.email,
                password=clean.password,
                full_name=clean.full_name,
                is_staff=True,
                is_superuser=True,
            )
            OrganizationMembership.objects.create(
                user=owner,
                organization=organization,
                role=EmployeeRole.OWNER,
                position_title="Владелец",
                totp_required=False,
            )
            record_audit_event(
                organization=organization,
                actor=owner,
                action="identity.instance_setup_completed",
                object_type="Organization",
                object_id=str(organization.public_id),
                payload={"organizationName": organization.name, "installDemo": clean.install_demo},
            )
            if clean.install_demo:
                # Демо ставит worker по outbox-событию; форма не ждёт.
                from chatballs.identity.demo_seed.service import request_install

                request_install(
                    context=TenantContext.for_resource(
                        organization, actor_kind=TenantActorKind.SYSTEM, actor_user=owner
                    ),
                    actor=owner,
                )
    return SetupResult(organization=organization, owner=owner)
