"""Мастер первого запуска (SPEC-CHATBALLS-0031, open source: «развернуть за минуту»).

Пока в инстансе нет ни одной организации, публичный эндпоинт /api/v1/setup/
принимает одну форму: название организации, имя, e-mail и пароль владельца.
Никаких параметров в .env и CLI: всё задаёт человек в браузере. После
создания владельца мастер закрывается навсегда (409).

Запись идёт по основному соединению процесса. Роль app вправе вставить
организацию только пока их нет (политика tenancy/0032); дальше создавать
организации может только роль platform (SPEC-HUB-0021 §10). Так пароль
platform-роли не нужен процессу backend-app.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import connections, transaction
from django.utils import translation
from django.utils.text import slugify

from chatballs.ai.knowledge_categories import ensure_uncategorized_category
from chatballs.i18n import INHERIT, current_language, normalize_language, t
from chatballs.identity.audit import record_audit_event
from chatballs.identity.instance_settings import remember_default_language, remember_public_host
from chatballs.identity.models import (
    EmployeeRole,
    HumanUser,
    Organization,
    OrganizationMembership,
    OrganizationStatus,
)
from chatballs.tenancy.context import TenantActorKind, TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import organization_route_by_slug
from chatballs.tenancy.lookup import instance_has_organizations, reserve_organization_id

ORGANIZATION_NAME_MAX_LENGTH = 255
FULL_NAME_MAX_LENGTH = 255

# Мастер работает по основному соединению процесса: отдельный алиас с ролью
# platform ему больше не нужен.
INSTANCE_DB_ALIAS = "default"


class SetupAlreadyCompleted(Exception):
    """Организация уже есть — мастер закрыт."""


@dataclass(frozen=True)
class SetupInput:
    organization_name: str
    full_name: str
    email: str
    password: str
    install_demo: bool = False
    # Язык установки, выбранный в мастере. Пусто — язык браузера, на котором
    # мастер и открылся: человек его не трогал, значит он верен.
    language: str = INHERIT


@dataclass(frozen=True)
class SetupResult:
    organization: Organization
    owner: HumanUser


def instance_needs_setup() -> bool:
    """Мастер нужен, пока не создана ни одна организация.

    Строки организаций роли app без контекста не видны (tenancy/0033):
    наличие хотя бы одной проверяет SECURITY DEFINER-функция.
    """
    return not instance_has_organizations()


def _clean(data: SetupInput) -> SetupInput:
    errors: dict[str, str] = {}
    organization_name = data.organization_name.strip()
    if not organization_name:
        errors["organizationName"] = t("admin.organization_name_required")
    elif len(organization_name) > ORGANIZATION_NAME_MAX_LENGTH:
        errors["organizationName"] = t("admin.name_too_long")
    full_name = " ".join(data.full_name.split())
    if not full_name:
        errors["fullName"] = t("setup.your_name_required")
    elif len(full_name) > FULL_NAME_MAX_LENGTH:
        errors["fullName"] = t("setup.your_name_too_long")
    email = data.email.strip()
    try:
        validate_email(email)
    except ValidationError:
        errors["email"] = t("setup.email_invalid")
    if errors:
        raise ValidationError(errors)
    return SetupInput(
        organization_name=organization_name,
        full_name=full_name,
        email=HumanUser.objects.normalize_email(email).lower(),
        password=data.password,
        install_demo=data.install_demo,
        language=normalize_language(data.language),
    )


def _unique_slug(name: str) -> str:
    base = slugify(name)[:40].strip("-") or "organization"
    candidate = base
    suffix = 2
    while organization_route_by_slug(candidate) is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def complete_setup(
    data: SetupInput, public_host: str = "", public_scheme: str = "http"
) -> SetupResult:
    """Создать установку целиком: язык, организация, владелец, демо-данные.

    Язык выбирается первым и держится активным до конца: на нём написана
    должность владельца, на нём приедут демо-данные и на нём вернутся ошибки
    формы. Иначе установка на английском получила бы русскую запись «Владелец»
    в карточке сотрудника — с первой же секунды и навсегда.
    """

    # Пусто — берём язык, который middleware уже вывела из Accept-Language:
    # именно на нём человек видел форму, пока её заполнял.
    language = normalize_language(data.language) or current_language()
    with translation.override(language):
        return _complete_setup(data, language, public_host, public_scheme)


def _complete_setup(
    data: SetupInput, language: str, public_host: str, public_scheme: str
) -> SetupResult:
    clean = _clean(data)
    with transaction.atomic(using=INSTANCE_DB_ALIAS):
        # Адрес, на котором человек прошёл мастер, и есть публичный адрес
        # установки: другого источника у коробки нет.
        if public_host:
            remember_public_host(public_host, public_scheme)
        remember_default_language(language)
        # Блокировка от гонки двух вкладок: второй запрос дождётся первого и
        # увидит созданную организацию.
        with connections[INSTANCE_DB_ALIAS].cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(hashtext('chatballs.instance_setup'))")
        if instance_has_organizations(using=INSTANCE_DB_ALIAS):
            raise SetupAlreadyCompleted()

        # Пароль проверяется против атрибутов будущего пользователя (схожесть
        # с e-mail и именем) до записи чего-либо.
        probe = HumanUser(email=clean.email, full_name=clean.full_name)
        validate_password(clean.password, user=probe)

        # id выделяется заранее: строка организации видна роли app только в
        # её контексте, и вставка идёт уже внутри него (tenancy/0033).
        organization_id = reserve_organization_id(using=INSTANCE_DB_ALIAS)
        with tenant_atomic(organization_id, using=INSTANCE_DB_ALIAS):
            organization = Organization(
                id=organization_id,
                name=clean.organization_name,
                slug=_unique_slug(clean.organization_name),
                status=OrganizationStatus.ACTIVE,
            )
            organization.save(force_insert=True)
            ensure_uncategorized_category(organization)
            owner = HumanUser.objects.create_user(
                email=clean.email,
                password=clean.password,
                full_name=clean.full_name,
                is_staff=True,
                is_superuser=True,
                is_instance_admin=True,
            )
            OrganizationMembership.objects.create(
                user=owner,
                organization=organization,
                role=EmployeeRole.OWNER,
                position_title=t("setup.owner_position"),
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
