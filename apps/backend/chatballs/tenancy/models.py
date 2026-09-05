from __future__ import annotations

from typing import ClassVar

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models


class TenantRelationModel(models.Model):
    """Direct tenant key derived from, and checked against, parent relations."""

    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="+",
    )
    tenant_relation_fields: ClassVar[tuple[str, ...]] = ()

    class Meta:
        abstract = True

    def _related_organization_ids(self) -> set[int]:
        organization_ids: set[int] = set()
        for field_name in self.tenant_relation_fields:
            try:
                related = getattr(self, field_name)
            except ObjectDoesNotExist:
                continue
            if related is None:
                continue
            organization_id = getattr(related, "organization_id", None)
            if organization_id is not None:
                organization_ids.add(int(organization_id))
        return organization_ids

    def validate_tenant_relations(self) -> None:
        organization_ids = self._related_organization_ids()
        if len(organization_ids) > 1:
            raise ValidationError("Tenant relations must belong to one organization")
        if self.organization_id is None:
            if not organization_ids:
                raise ValidationError("Tenant-owned row requires an organization")
            self.organization_id = next(iter(organization_ids))
        elif organization_ids and organization_ids != {int(self.organization_id)}:
            raise ValidationError("Tenant relation does not match organization")

    def clean(self) -> None:
        super().clean()
        self.validate_tenant_relations()

    def save(self, *args: object, **kwargs: object) -> None:
        self.validate_tenant_relations()
        super().save(*args, **kwargs)


class OrganizationStorageUsage(models.Model):
    """Authoritative storage_bytes usage counter for one organization.

    ``bytes_used`` is the committed total; ``reserved_bytes`` covers in-flight
    uploads whose final size is not yet known (SPEC-HUB-0022 §10 reserve/finalize).
    The effective usage against the quota is ``bytes_used + reserved_bytes``.
    """

    organization = models.OneToOneField(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="storage_usage",
    )
    bytes_used = models.PositiveBigIntegerField(default=0)
    reserved_bytes = models.PositiveBigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(bytes_used__gte=0),
                name="storage_usage_bytes_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_bytes__gte=0),
                name="storage_usage_reserved_non_negative",
            ),
        ]


class StorageReservation(models.Model):
    """An in-flight storage_bytes reservation keyed by an idempotency token, so a
    multi-step upload (SPEC-HUB-0022 §10) can reserve the expected size, finalize
    the actual size once the object is persisted, and release the reservation on
    failure. A single reservation tracks one upload lifecycle.
    """

    organization = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="storage_reservations",
    )
    idempotency_key = models.CharField(max_length=160)
    reserved_bytes = models.PositiveBigIntegerField()
    finalized = models.BooleanField(default=False)
    released = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Only one *active* reservation per idempotency key per org. Once a
            # reservation is finalized or released the same key may be reused for a
            # later upload (e.g. re-upload replacing a file with the same name).
            models.UniqueConstraint(
                fields=["organization", "idempotency_key"],
                condition=models.Q(finalized=False, released=False),
                name="uniq_storage_reservation_active",
            ),
        ]

    def __str__(self) -> str:
        state = "finalized" if self.finalized else "released" if self.released else "active"
        return f"{self.organization_id}:{self.idempotency_key}:{state}"


# Настройки хранилища инстанса живут в отдельном модуле; импорт нужен, чтобы Django увидел модель.
from chatballs.tenancy.storage_settings import StorageSettings  # noqa: E402,F401
