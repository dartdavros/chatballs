from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from chatballs.ai.knowledge_categories import (
    create_category,
    delete_category,
    ensure_uncategorized_category,
    move_category,
    rename_category,
)
from chatballs.ai.knowledge_types import (
    UNCATEGORIZED_CATEGORY_NAME,
)
from chatballs.ai.models import Knowledge, KnowledgeCategory
from chatballs.identity.models import Organization
from chatballs.tenancy.context import TenantContext


class KnowledgeCategoryTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Example", slug="knowledge-example")
        self.other_organization = Organization.objects.create(
            name="Other", slug="knowledge-other"
        )
        ensure_uncategorized_category(self.organization)
        ensure_uncategorized_category(self.other_organization)
        self.context = TenantContext.for_resource(self.organization)

    def test_system_category_creation_is_idempotent(self) -> None:
        first = ensure_uncategorized_category(self.organization)
        second = ensure_uncategorized_category(self.organization)
        category = KnowledgeCategory.objects.get(
            organization=self.organization,
            is_system=True,
        )

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(category.name, UNCATEGORIZED_CATEGORY_NAME)
        self.assertIsNone(category.parent_id)
        self.organization.name = "Renamed"
        self.organization.save(update_fields=["name"])
        self.assertEqual(
            KnowledgeCategory.objects.filter(
                organization=self.organization,
                is_system=True,
            ).count(),
            1,
        )

    def test_tree_is_deterministically_ordered(self) -> None:
        root = create_category(context=self.context, name="Products", sort_order=10)
        create_category(context=self.context, parent=root, name="Zulu", sort_order=20)
        create_category(context=self.context, parent=root, name="Alpha", sort_order=20)
        create_category(context=self.context, parent=root, name="First", sort_order=10)

        self.assertEqual(
            list(root.children.values_list("name", flat=True)),
            ["First", "Alpha", "Zulu"],
        )

    def test_sibling_name_is_unique_for_root_and_nested_categories(self) -> None:
        create_category(context=self.context, name="Products")
        with self.assertRaises(ValidationError):
            create_category(context=self.context, name="Products")

        parent = create_category(context=self.context, name="Company")
        create_category(context=self.context, parent=parent, name="FAQ")
        with self.assertRaises(ValidationError):
            create_category(context=self.context, parent=parent, name="FAQ")

    def test_blank_name_and_cross_tenant_parent_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            create_category(context=self.context, name="   ")

        other_parent = KnowledgeCategory.objects.create(
            organization=self.other_organization,
            name="Other parent",
        )
        with self.assertRaises(ValidationError):
            create_category(context=self.context, name="Invalid", parent=other_parent)

    def test_move_rejects_cycle_and_cross_tenant_parent(self) -> None:
        root = create_category(context=self.context, name="Root")
        child = create_category(context=self.context, name="Child", parent=root)
        grandchild = create_category(context=self.context, name="Grandchild", parent=child)

        with self.assertRaises(ValidationError):
            move_category(
                context=self.context,
                category=root,
                parent=grandchild,
            )
        root.refresh_from_db()
        self.assertIsNone(root.parent_id)

        other_parent = KnowledgeCategory.objects.create(
            organization=self.other_organization,
            name="Other",
        )
        with self.assertRaises(ValidationError):
            move_category(
                context=self.context,
                category=child,
                parent=other_parent,
            )

    def test_system_category_is_immutable_and_cannot_be_deleted(self) -> None:
        system = KnowledgeCategory.objects.get(
            organization=self.organization,
            is_system=True,
        )

        with self.assertRaises(ValidationError):
            rename_category(context=self.context, category=system, name="Other")
        with self.assertRaises(ValidationError):
            move_category(context=self.context, category=system, parent=None, sort_order=5)
        with self.assertRaises(ValidationError):
            delete_category(context=self.context, category=system)

    def test_delete_only_allows_empty_leaf(self) -> None:
        parent = create_category(context=self.context, name="Parent")
        child = create_category(context=self.context, name="Child", parent=parent)
        with self.assertRaises(ValidationError):
            delete_category(context=self.context, category=parent)

        knowledge = Knowledge.objects.create(
            organization=self.organization,
            category=child,
            title="FAQ",
        )
        with self.assertRaises(ValidationError):
            delete_category(context=self.context, category=child)

        knowledge.delete()
        delete_category(context=self.context, category=child)
        self.assertFalse(KnowledgeCategory.objects.filter(pk=child.pk).exists())

    def test_knowledge_rejects_category_from_another_organization(self) -> None:
        category = KnowledgeCategory.objects.get(
            organization=self.other_organization,
            is_system=True,
        )

        with self.assertRaises(ValidationError):
            Knowledge.objects.create(
                organization=self.organization,
                category=category,
                title="Invalid",
            )

    def test_database_prevents_second_system_category(self) -> None:
        with self.assertRaises((ValidationError, IntegrityError)):
            with transaction.atomic():
                KnowledgeCategory.objects.create(
                    organization=self.organization,
                    name=UNCATEGORIZED_CATEGORY_NAME,
                    is_system=True,
                )
