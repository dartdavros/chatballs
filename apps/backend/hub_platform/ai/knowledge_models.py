from django.core.exceptions import ValidationError
from django.db import models

from hub_platform.ai.knowledge_types import UNCATEGORIZED_CATEGORY_NAME
from hub_platform.tenancy.models import TenantRelationModel


class KnowledgeCategory(TenantRelationModel):
    tenant_relation_fields = ("parent",)

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    sort_order = models.IntegerField(default=0)
    is_system = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "parent", "name"],
                name="uniq_knowledge_category_sibling_name",
                nulls_distinct=False,
            ),
            models.UniqueConstraint(
                fields=["organization"],
                condition=models.Q(is_system=True),
                name="uniq_system_knowledge_category_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(is_system=False) | models.Q(parent__isnull=True),
                name="system_knowledge_category_is_root",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.name = self.name.strip()
        if not self.name:
            raise ValidationError({"name": "Category name is required"})
        persisted = None
        if self.pk is not None:
            persisted = type(self).objects.filter(pk=self.pk).values("is_system").first()
        if persisted and persisted["is_system"] and not self.is_system:
            raise ValidationError({"category": "System category is immutable"})
        if self.is_system and self.name != UNCATEGORIZED_CATEGORY_NAME:
            raise ValidationError({"name": "System category name is immutable"})

        ancestor = self.parent
        visited: set[int] = set()
        while ancestor is not None:
            if self.pk is not None and ancestor.pk == self.pk:
                raise ValidationError({"parent": "Category cycle is not allowed"})
            if ancestor.pk is not None:
                if ancestor.pk in visited:
                    raise ValidationError({"parent": "Category cycle is not allowed"})
                visited.add(ancestor.pk)
            ancestor = ancestor.parent

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object):
        if self.is_system:
            raise ValidationError({"category": "System category cannot be deleted"})
        if self.children.exists():
            raise ValidationError({"category": "Category with children cannot be deleted"})
        if self.knowledge_items.exists():
            raise ValidationError({"category": "Category with knowledge cannot be deleted"})
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"category:{self.organization_id}/{self.name}"


class KnowledgeDepartment(TenantRelationModel):
    tenant_relation_fields = ("knowledge", "department")

    knowledge = models.ForeignKey(
        "ai.Knowledge",
        on_delete=models.CASCADE,
        related_name="department_links",
    )
    department = models.ForeignKey(
        "identity.Department",
        on_delete=models.PROTECT,
        related_name="knowledge_links",
    )

    class Meta:
        ordering = ["department__name", "department_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["knowledge", "department"],
                name="uniq_knowledge_department",
            )
        ]

    def clean(self) -> None:
        super().clean()
        from hub_platform.identity.models import DepartmentStatus

        if self.department.status != DepartmentStatus.ACTIVE:
            raise ValidationError({"department": "Disabled department is not allowed"})

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"knowledge-department:{self.knowledge_id}/{self.department_id}"
