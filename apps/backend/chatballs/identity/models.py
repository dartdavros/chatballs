from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from chatballs.identity.crypto import EncryptedCharField
from chatballs.identity.operation_modes import OperationMode
from chatballs.identity.work_status_codes import WorkStatus


class HumanUserManager(UserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: object) -> HumanUser:
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> HumanUser:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: object) -> HumanUser:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class UiTheme(models.TextChoices):
    # Персональная тема интерфейса (дизайн-базлайн v2, SPEC-CHATBALLS-0031 §7).
    LIGHT = "LIGHT", "Светлая"
    DARK = "DARK", "Тёмная"
    SYSTEM = "SYSTEM", "Как в системе"


def user_storage():
    from django.core.files.storage import storages

    return storages["users"]


def user_avatar_upload_path(instance: HumanUser, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"users/{instance.id}/avatar-{uuid.uuid4()}{suffix}"


class HumanUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    must_change_password = models.BooleanField(default=False)
    # «Последняя смена пароля» в карточке сотрудника (кадр E3).
    password_changed_at = models.DateTimeField(null=True, blank=True, db_default=None)
    totp_enabled = models.BooleanField(default=False)
    totp_secret = EncryptedCharField(max_length=255, blank=True)
    # Когда последний раз принимался код аутентификатора — подпись в карточке
    # «Двухфакторная аутентификация» (дизайн-базлайн v2, кадр P1).
    totp_last_used_at = models.DateTimeField(null=True, blank=True, db_default=None)
    # Номер последнего принятого интервала TOTP (RFC 6238 §5.2). Код живёт
    # 30 секунд и принимается с окном ±1 интервал, то есть подсмотренный код
    # без этой отметки принимался бы второй раз ещё полторы минуты.
    totp_last_counter = models.BigIntegerField(default=0)
    # Внешний вид — глобальная настройка пользователя (не membership):
    # тема и акцентный HEX-цвет; пустой акцент — цвет продукта #0f9b8e.
    ui_theme = models.CharField(max_length=8, choices=UiTheme.choices, default=UiTheme.SYSTEM)
    ui_accent = models.CharField(max_length=9, blank=True)
    # Язык интерфейса — тоже глобальная настройка пользователя, а не
    # membership: человек читает на одном языке во всех организациях, куда
    # входит. Пустая строка — «как в организации»: это не английский и не
    # русский, а отсутствие личного выбора, и она переживает смену языка
    # организации, тогда как записанный при регистрации код — нет.
    ui_language = models.CharField(max_length=5, blank=True, default="")
    # Администратор установки: право менять свойства инсталляции — адрес,
    # почту, TURN, хранилище файлов. Это не роль в организации, а признак
    # учётной записи: первым его получает владелец из мастера первого
    # запуска, дальше его передают командой set_instance_admin.
    is_instance_admin = models.BooleanField(default=False)
    # Фото сотрудника (дизайн-базлайн v2): видно коллегам в сайдбаре, подписи
    # сообщений, выборе ответственного. Загружается в профиле.
    avatar = models.FileField(upload_to=user_avatar_upload_path, storage=user_storage, max_length=512, blank=True, default="")
    avatar_content_type = models.CharField(max_length=64, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    objects = HumanUserManager()

    def __str__(self) -> str:
        return self.email

class OrganizationStatus(models.TextChoices):
    # PENDING_OWNER до принятия OWNER invitation, ACTIVE после.
    ACTIVE = "ACTIVE", "Active"
    PENDING_OWNER = "PENDING_OWNER", "Pending owner"


def organization_logo_upload_path(instance: Organization, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return (
        f"organizations/{instance.public_id}/branding/"
        f"logo-{uuid.uuid4()}{suffix}"
    )


class Organization(models.Model):
    external_execution_enabled = models.BooleanField(default=False, db_default=False)
    external_execution_version = models.PositiveBigIntegerField(default=1, db_default=1)
    operation_mode = models.CharField(max_length=16, choices=OperationMode.choices, default=OperationMode.AI_AGENTS)
    operation_mode_version = models.PositiveBigIntegerField(default=1)
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    status = models.CharField(
        max_length=32,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
    )
    timezone = models.CharField(max_length=64, default="Europe/Moscow")
    # Язык рабочего места по умолчанию: на нём организация открывается всем,
    # кто не выбрал свой в профиле. Стоит рядом с часовым поясом и валютой —
    # это такой же региональный параметр организации, и в «Настройках» они
    # лежат в одном разделе.
    language = models.CharField(max_length=5, blank=True, default="")
    # SPEC-0026: additional active participants per conversation; assignment is excluded.
    # Lowering this setting preserves existing participation history and active rows.
    additional_participant_limit = models.PositiveIntegerField(default=5, db_default=5)
    logo = models.FileField(
        upload_to=organization_logo_upload_path,
        max_length=512,
        blank=True,
        default="",
        db_default="",
    )
    logo_content_type = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_default="",
    )
    logo_size = models.PositiveBigIntegerField(default=0, db_default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(public_id=self.public_id).exists():
            raise ValidationError({"public_id": "Organization public_id is immutable"})
        super().save(*args, **kwargs)


# SPEC-CHATBALLS-0016 §5: лимит должности задаётся backend-константой.
POSITION_TITLE_MAX_LENGTH = 120


class EmployeeRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    SUPERVISOR = "SUPERVISOR", "Supervisor"
    EMPLOYEE = "EMPLOYEE", "Employee"


class OrganizationMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=EmployeeRole.choices)
    # Должность вводится вручную; обязательна для новых записей (SPEC-CHATBALLS-0016 §5).
    # Пустая строка допускается на уровне БД только для legacy-записей до backfill.
    position_title = models.CharField(max_length=POSITION_TITLE_MAX_LENGTH, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True)
    totp_required = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    work_status = models.CharField(max_length=16, choices=WorkStatus.choices, default=WorkStatus.UNAVAILABLE, db_default=WorkStatus.UNAVAILABLE)
    work_status_version = models.PositiveBigIntegerField(default=0, db_default=0)
    work_status_changed_at = models.DateTimeField(null=True, blank=True, db_default=None)
    # Онбординг закрыт этим человеком в этой организации. Признак живёт на
    # членстве, а не на организации: иначе первый же закрывший спрятал бы
    # визард всей команде. NULL — не закрывал, значит увидит при следующем
    # входе, включая тех, кто работает в системе давно.
    onboarding_dismissed_at = models.DateTimeField(null=True, blank=True)
    # Визард пройден до конца. Отдельно от «закрыл»: закрыть можно на первом
    # шаге, и тогда возвращаться к настройке ещё есть зачем.
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Preserve the deployed table and every existing PK/FK during C02 rename.
        db_table = "identity_employeeprofile"
        constraints = [
            models.CheckConstraint(condition=Q(work_status__in=WorkStatus.values), name="membership_work_status_valid"),
            models.CheckConstraint(condition=Q(work_status_version=0, work_status_changed_at__isnull=True, work_status=WorkStatus.UNAVAILABLE) | Q(work_status_version__gt=0, work_status_changed_at__isnull=False), name="membership_work_status_initial"),
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="uniq_membership_user_organization",
            ),
            # В организации ровно один владелец (SPEC-CHATBALLS-0031 §3).
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(role=EmployeeRole.OWNER),
                name="uniq_owner_per_organization",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}:{self.user.email}:{self.role}"

    @property
    def is_blocked(self) -> bool:
        return self.blocked_at is not None

    def block(self) -> None:
        self.blocked_at = timezone.now()
        self.save(update_fields=["blocked_at"])

    def unblock(self) -> None:
        self.blocked_at = None
        self.save(update_fields=["blocked_at"])


# Django imports only models.py by convention. Re-export related models after the core
# identity entities are defined so they are registered without growing this file.
from chatballs.identity.audit_models import (  # noqa: E402, F401
    AuditEvent,
    AuditResult,
)
from chatballs.identity.demo_models import (  # noqa: E402, F401
    DemoDataset,
    DemoRecord,
)
from chatballs.identity.group_models import (  # noqa: E402, F401
    EmployeeGroup,
    EmployeeGroupMember,
)
from chatballs.identity.instance_settings import (  # noqa: E402, F401
    InstanceSettings,
)
from chatballs.identity.invitation_models import (  # noqa: E402, F401
    OrganizationInvitation,
)
from chatballs.identity.supervision_models import (  # noqa: E402, F401
    EmployeeGroupSupervision,
)
from chatballs.identity.work_status_models import (  # noqa: E402, F401
    WorkStatusOperation,
)
