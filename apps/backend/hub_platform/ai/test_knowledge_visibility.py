from django.core.exceptions import ValidationError
from django.test import TestCase

from hub_platform.ai.knowledge_categories import ensure_uncategorized_category
from hub_platform.ai.knowledge_types import KnowledgeVisibility
from hub_platform.ai.knowledge_visibility import replace_knowledge_visibility
from hub_platform.ai.models import Knowledge, KnowledgeCategory, KnowledgeDepartment
from hub_platform.identity.models import (
    Department,
    DepartmentStatus,
    Organization,
)
from hub_platform.tenancy.context import TenantContext


class KnowledgeVisibilityTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="visibility-example")
        self.other_organization = Organization.objects.create(
            name="Other", slug="visibility-other"
        )
        ensure_uncategorized_category(self.organization)
        ensure_uncategorized_category(self.other_organization)
        self.context = TenantContext.for_resource(self.organization)
        self.sales = Department.objects.create(
            organization=self.organization,
            code="sales",
            name="Sales",
        )
        self.support = Department.objects.create(
            organization=self.organization,
            code="support",
            name="Support",
        )
        self.disabled = Department.objects.create(
            organization=self.organization,
            code="disabled",
            name="Disabled",
            status=DepartmentStatus.DISABLED,
        )
        self.other_department = Department.objects.create(
            organization=self.other_organization,
            code="other",
            name="Other",
        )
        self.knowledge = Knowledge.objects.create(
            organization=self.organization,
            category=KnowledgeCategory.objects.get(
                organization=self.organization,
                is_system=True,
            ),
            title="Shared knowledge",
        )

    def test_department_visibility_requires_active_same_tenant_departments(self) -> None:
        for invalid_ids in ([], [self.disabled.id], [self.other_department.id], [999999]):
            with self.subTest(department_ids=invalid_ids):
                with self.assertRaises(ValidationError):
                    replace_knowledge_visibility(
                        context=self.context,
                        knowledge=self.knowledge,
                        visibility=KnowledgeVisibility.DEPARTMENTS,
                        department_ids=invalid_ids,
                    )

        self.knowledge.refresh_from_db()
        self.assertEqual(self.knowledge.visibility, KnowledgeVisibility.ORGANIZATION)
        self.assertFalse(self.knowledge.department_links.exists())

    def test_department_visibility_replaces_links_atomically(self) -> None:
        replace_knowledge_visibility(
            context=self.context,
            knowledge=self.knowledge,
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=[self.sales.id, self.support.id, self.sales.id],
        )
        self.assertEqual(
            set(self.knowledge.departments.values_list("id", flat=True)),
            {self.sales.id, self.support.id},
        )

        with self.assertRaises(ValidationError):
            replace_knowledge_visibility(
                context=self.context,
                knowledge=self.knowledge,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=[self.disabled.id],
            )
        self.knowledge.refresh_from_db()
        self.assertEqual(self.knowledge.visibility, KnowledgeVisibility.DEPARTMENTS)
        self.assertEqual(
            set(self.knowledge.departments.values_list("id", flat=True)),
            {self.sales.id, self.support.id},
        )

    def test_organization_visibility_requires_and_restores_empty_links(self) -> None:
        replace_knowledge_visibility(
            context=self.context,
            knowledge=self.knowledge,
            visibility=KnowledgeVisibility.DEPARTMENTS,
            department_ids=[self.sales.id],
        )
        with self.assertRaises(ValidationError):
            replace_knowledge_visibility(
                context=self.context,
                knowledge=self.knowledge,
                visibility=KnowledgeVisibility.ORGANIZATION,
                department_ids=[self.sales.id],
            )

        replace_knowledge_visibility(
            context=self.context,
            knowledge=self.knowledge,
            visibility=KnowledgeVisibility.ORGANIZATION,
            department_ids=[],
        )
        self.knowledge.refresh_from_db()
        self.assertEqual(self.knowledge.visibility, KnowledgeVisibility.ORGANIZATION)
        self.assertFalse(self.knowledge.department_links.exists())

    def test_unknown_visibility_and_non_integer_ids_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            replace_knowledge_visibility(
                context=self.context,
                knowledge=self.knowledge,
                visibility="PUBLIC",
                department_ids=[],
            )
        with self.assertRaises(ValidationError):
            replace_knowledge_visibility(
                context=self.context,
                knowledge=self.knowledge,
                visibility=KnowledgeVisibility.DEPARTMENTS,
                department_ids=["sales"],
            )

    def test_direct_through_link_rejects_cross_tenant_and_disabled_department(self) -> None:
        self.knowledge.visibility = KnowledgeVisibility.DEPARTMENTS
        self.knowledge.save(update_fields=["visibility"])
        with self.assertRaises(ValidationError):
            KnowledgeDepartment.objects.create(
                organization=self.organization,
                knowledge=self.knowledge,
                department=self.other_department,
            )
        with self.assertRaises(ValidationError):
            KnowledgeDepartment.objects.create(
                organization=self.organization,
                knowledge=self.knowledge,
                department=self.disabled,
            )
