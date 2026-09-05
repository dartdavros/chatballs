from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower

from hub_platform.identity.models import Organization, OrganizationMembership
from hub_platform.tenancy.models import TenantRelationModel

# Настраиваемые группы сотрудников (ADR-HUB-0043): граница видимости диалогов
# и ничего больше — без прав, знаний, должностей и иерархии. Организация сама
# решает, какие группы ей нужны; групп может не быть вообще.


class EmployeeGroup(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="employee_groups"
    )
    name = models.CharField(max_length=120)
    # Цвет точки группы в чате (дизайн-базлайн v2); пустой — палитра по id.
    color = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "organization", name="uniq_employee_group_org_name_ci"
            )
        ]

    def clean(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Group name is required"})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.name}"


class EmployeeGroupMember(TenantRelationModel):
    tenant_relation_fields = ("group", "employee")
    group = models.ForeignKey(
        EmployeeGroup, on_delete=models.CASCADE, related_name="member_links"
    )
    employee = models.ForeignKey(
        OrganizationMembership, on_delete=models.CASCADE, related_name="group_links"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "employee"], name="uniq_employee_group_member"
            )
        ]

    def save(self, *args, **kwargs) -> None:
        self.validate_tenant_relations()
        super().save(*args, **kwargs)


def member_group_ids(membership: OrganizationMembership) -> set[int]:
    """Группы сотрудника; используется политикой видимости диалогов."""
    return set(
        EmployeeGroupMember.objects.filter(employee=membership).values_list(
            "group_id", flat=True
        )
    )
