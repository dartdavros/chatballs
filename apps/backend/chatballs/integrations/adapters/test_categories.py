"""Adapter categories are explicit presentation metadata, not permission scopes."""

from dataclasses import replace

from django.test import SimpleTestCase

from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.adapters.categories import OperationCategory
from chatballs.integrations.adapters.registry import build_registry
from chatballs.integrations.adapters.validation import validate_adapter
from chatballs.integrations.execution.snapshots import signature


class OperationCategoryTests(SimpleTestCase):
    def test_bitrix_categories_are_explicit_and_optional_for_general_operations(self):
        for entity in ("lead", "deal", "contact"):
            for verb in ("create", "get", "update", "delete", "list"):
                self.assertEqual([item.key for item in ADAPTER.operation(f"{entity}.{verb}").category_path], ["crm"])
        self.assertEqual([item.key for item in ADAPTER.operation("lead_stage.list").category_path], ["crm"])
        self.assertEqual([item.key for item in ADAPTER.operation("user.list").category_path], ["users"])
        self.assertEqual(ADAPTER.operation("scope.get").category_path, ())
        self.assertEqual(ADAPTER.operation("batch").category_path, ())

    def test_categories_do_not_change_execution_contract_or_follow_permissions(self):
        operation = ADAPTER.operation("lead.create")
        changed = replace(operation, category_path=(OperationCategory("custom", "runs.catalog_scenarios"),))
        self.assertEqual(signature(operation), signature(changed))
        self.assertEqual(replace(operation, permission_scope="user").category_path, operation.category_path)

    def test_invalid_descriptor_category_is_rejected_at_registration(self):
        registry = build_registry([])
        operation = replace(ADAPTER.operation("lead.create"), category_path=(OperationCategory("Bad category", ""),))
        descriptor = replace(ADAPTER, operations=(operation,), entities=(), templates=(), lookups=(),
                             auth_methods=tuple(replace(method, check=None) for method in ADAPTER.auth_methods))
        self.assertTrue(any("bad category" in message for message in validate_adapter(descriptor, registry)))
