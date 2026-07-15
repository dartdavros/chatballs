from __future__ import annotations

import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from hub_platform.identity.crypto import EncryptedCharField


class HumanUserManager(UserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: object) -> "HumanUser":
        if not email:
            raise ValueError("The email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields: object) -> "HumanUser":
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: object) -> "HumanUser":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class HumanUser(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    must_change_password = models.BooleanField(default=False)
    totp_enabled = models.BooleanField(default=False)
    totp_secret = EncryptedCharField(max_length=255, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []
    objects = HumanUserManager()

    def __str__(self) -> str:
        return self.email

class TaxRegime(models.TextChoices):
    USN_INCOME = "USN_INCOME", "УСН доходы"


class VatMode(models.TextChoices):
    WITHOUT_VAT = "WITHOUT_VAT", "Без НДС"


class Organization(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    timezone = models.CharField(max_length=64, default="Europe/Moscow")
    currency = models.CharField(max_length=3, default="RUB")
    tax_regime = models.CharField(max_length=32, choices=TaxRegime.choices, default=TaxRegime.USN_INCOME)
    vat_mode = models.CharField(max_length=32, choices=VatMode.choices, default=VatMode.WITHOUT_VAT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exclude(public_id=self.public_id).exists():
            raise ValidationError({"public_id": "Organization public_id is immutable"})
        super().save(*args, **kwargs)


class DepartmentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    DISABLED = "DISABLED", "Disabled"


class Department(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="departments")
    code = models.SlugField(max_length=64)
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32,
        choices=DepartmentStatus.choices,
        default=DepartmentStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="uniq_department_org_code")
        ]

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.code}"


# ADR-HUB-0027 / SPEC-HUB-0016 §5: лимит должности задаётся backend-константой.
POSITION_TITLE_MAX_LENGTH = 120


class EmployeeRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
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
    # Должность вводится вручную; обязательна для новых записей (SPEC-HUB-0016 §5).
    # Пустая строка допускается на уровне БД только для legacy-записей до backfill.
    position_title = models.CharField(max_length=POSITION_TITLE_MAX_LENGTH, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True)
    # Основной отдел описывает оргструктуру, но не выдаёт прав (ADR-HUB-0027).
    # null = сотрудник на верхнем уровне компании; OWNER всегда на уровне компании.
    primary_department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="memberships",
        null=True,
        blank=True,
    )
    totp_required = models.BooleanField(default=False)
    blocked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Preserve the deployed table and every existing PK/FK during C02 rename.
        db_table = "identity_employeeprofile"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="uniq_membership_user_organization",
            ),
            # OWNER всегда на уровне компании (ADR-HUB-0027, инварианты размещения).
            models.CheckConstraint(
                condition=~Q(role=EmployeeRole.OWNER) | Q(primary_department__isnull=True),
                name="owner_is_company_level",
            ),
            # В организации ровно один владелец (ADR-HUB-0027).
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


class AuditResult(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    DENIED = "DENIED", "Denied"
    FAILED = "FAILED", "Failed"


class AuditEvent(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="audit_events",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=128)
    object_type = models.CharField(max_length=128, blank=True)
    object_id = models.CharField(max_length=128, blank=True)
    result = models.CharField(max_length=32, choices=AuditResult.choices, default=AuditResult.SUCCESS)
    payload = models.JSONField(default=dict, blank=True)
    correlation_id = models.CharField(max_length=128, blank=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action}:{self.result}"


# Django imports only models.py by convention. Re-export access models after the core
# identity entities are defined so they are registered without growing this file.
from hub_platform.identity.access_models import (  # noqa: E402, F401
    AccessProfile,
    AccessProfileCapability,
    EmployeeAccessAssignment,
)
from hub_platform.identity.invitation_models import (  # noqa: E402, F401
    OrganizationInvitation,
)
