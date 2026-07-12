from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractUser, UserManager
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
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    timezone = models.CharField(max_length=64, default="Europe/Moscow")
    currency = models.CharField(max_length=3, default="RUB")
    tax_regime = models.CharField(max_length=32, choices=TaxRegime.choices, default=TaxRegime.USN_INCOME)
    vat_mode = models.CharField(max_length=32, choices=VatMode.choices, default=VatMode.WITHOUT_VAT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


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


class EmployeeProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_profile")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="employees")
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
        related_name="employees",
        null=True,
        blank=True,
    )
    must_change_password = models.BooleanField(default=False)
    totp_required = models.BooleanField(default=False)
    totp_enabled = models.BooleanField(default=False)
    totp_secret = EncryptedCharField(max_length=255, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # OWNER всегда на уровне компании (ADR-HUB-0027, инварианты размещения).
            models.CheckConstraint(
                check=~Q(role=EmployeeRole.OWNER) | Q(primary_department__isnull=True),
                name="owner_is_company_level",
            ),
            # В организации ровно один владелец (ADR-HUB-0027).
            models.UniqueConstraint(
                fields=["organization"],
                condition=Q(role=EmployeeRole.OWNER),
                name="uniq_owner_per_organization",
            ),
        ]

    @property
    def is_blocked(self) -> bool:
        return self.blocked_at is not None

    def block(self) -> None:
        self.blocked_at = timezone.now()
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.save(update_fields=["blocked_at"])

    def __str__(self) -> str:
        return f"{self.user.email}:{self.role}"


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
