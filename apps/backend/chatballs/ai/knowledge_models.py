from django.core.exceptions import ValidationError
from django.db import models

from chatballs.ai.knowledge_types import UNCATEGORIZED_CATEGORY_NAME
from chatballs.i18n import t
from chatballs.tenancy.models import TenantRelationModel


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
            raise ValidationError({"name": t("ai.category_name_required")})
        persisted = None
        if self.pk is not None:
            persisted = type(self).objects.filter(pk=self.pk).values("is_system").first()
        if persisted and persisted["is_system"] and not self.is_system:
            raise ValidationError({"category": t("ai.system_category_immutable")})
        if self.is_system and self.name != UNCATEGORIZED_CATEGORY_NAME:
            raise ValidationError({"name": t("ai.system_category_name_immutable")})

        ancestor = self.parent
        visited: set[int] = set()
        while ancestor is not None:
            if self.pk is not None and ancestor.pk == self.pk:
                raise ValidationError({"parent": t("ai.category_cycle")})
            if ancestor.pk is not None:
                if ancestor.pk in visited:
                    raise ValidationError({"parent": t("ai.category_cycle")})
                visited.add(ancestor.pk)
            ancestor = ancestor.parent

    def save(self, *args: object, **kwargs: object) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args: object, **kwargs: object):
        if self.is_system:
            raise ValidationError({"category": t("ai.system_category_undeletable")})
        if self.children.exists():
            raise ValidationError({"category": t("ai.category_with_children")})
        if self.knowledge_items.exists():
            raise ValidationError({"category": t("ai.category_with_knowledge")})
        return super().delete(*args, **kwargs)

    def __str__(self) -> str:
        return f"category:{self.organization_id}/{self.name}"
