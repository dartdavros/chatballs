from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from hub_platform.identity.capabilities import CAPABILITY_REGISTRY, ScopeType, capability_spec
from hub_platform.identity.models import Department, Organization, OrganizationMembership
from hub_platform.tenancy.models import TenantRelationModel


class AccessProfile(models.Model):
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="access_profiles"
    )
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "organization", name="uniq_access_profile_org_name_ci"
            )
        ]

    def clean(self) -> None:
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Profile name is required"})

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.organization.slug}/{self.name}"


class AccessProfileCapability(TenantRelationModel):
    tenant_relation_fields = ("access_profile",)
    access_profile = models.ForeignKey(
        AccessProfile, on_delete=models.CASCADE, related_name="capability_links"
    )
    capability_code = models.CharField(max_length=80)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["access_profile", "capability_code"],
                name="uniq_access_profile_capability",
            ),
            models.CheckConstraint(
                condition=Q(
                    capability_code__in=[
                        code
                        for code, spec in CAPABILITY_REGISTRY.items()
                        if spec.assignable and not spec.protected
                    ]
                ),
                name="access_profile_capability_registry",
            ),
        ]

    def clean(self) -> None:
        try:
            spec = capability_spec(self.capability_code)
        except ValueError as error:
            raise ValidationError({"capability_code": str(error)}) from error
        if not spec.assignable or spec.protected:
            raise ValidationError({"capability_code": "Protected capability cannot be assigned"})

    def save(self, *args, **kwargs) -> None:
        self.validate_tenant_relations()
        self.full_clean()
        super().save(*args, **kwargs)


class EmployeeAccessAssignment(TenantRelationModel):
    tenant_relation_fields = (
        "employee",
        "access_profile",
        "department",
        "assigned_by",
    )
    employee = models.ForeignKey(
        OrganizationMembership,
        on_delete=models.PROTECT,
        related_name="access_assignments",
    )
    access_profile = models.ForeignKey(
        AccessProfile, on_delete=models.PROTECT, related_name="assignments"
    )
    scope_type = models.CharField(
        max_length=16,
        choices=((ScopeType.ORGANIZATION, "Organization"), (ScopeType.DEPARTMENT, "Department")),
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="access_assignments",
        null=True,
        blank=True,
    )
    assigned_by = models.ForeignKey(
        OrganizationMembership,
        on_delete=models.PROTECT,
        related_name="access_assignments_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(scope_type=ScopeType.ORGANIZATION, department__isnull=True))
                | (Q(scope_type=ScopeType.DEPARTMENT, department__isnull=False)),
                name="access_assignment_scope_department",
            ),
            models.UniqueConstraint(
                fields=["employee", "access_profile"],
                condition=Q(scope_type=ScopeType.ORGANIZATION, revoked_at__isnull=True),
                name="uniq_active_org_access_assignment",
            ),
            models.UniqueConstraint(
                fields=["employee", "access_profile", "department"],
                condition=Q(scope_type=ScopeType.DEPARTMENT, revoked_at__isnull=True),
                name="uniq_active_dept_access_assignment",
            ),
        ]

    def clean(self) -> None:
        organization_id = self.employee.organization_id
        if self.access_profile.organization_id != organization_id:
            raise ValidationError("Employee and access profile must belong to one organization")
        if self.assigned_by.organization_id != organization_id:
            raise ValidationError("Assigning employee must belong to the same organization")
        if self.department_id and self.department.organization_id != organization_id:
            raise ValidationError("Department must belong to the same organization")
        if not self.access_profile.is_active and self.revoked_at is None:
            raise ValidationError("Disabled access profile cannot be assigned")
        expected_department = self.scope_type == ScopeType.DEPARTMENT
        if expected_department != bool(self.department_id):
            raise ValidationError("Department is required only for DEPARTMENT scope")

    def save(self, *args, **kwargs) -> None:
        self.validate_tenant_relations()
        self.full_clean()
        super().save(*args, **kwargs)
