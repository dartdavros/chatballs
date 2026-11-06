"""Manual bindings and Bitrix user labels retain typed, explicit semantics."""

from dataclasses import replace

from django.test import SimpleTestCase

from chatballs.integrations.adapters.bitrix24 import ADAPTER
from chatballs.integrations.adapters.bitrix24.descriptor import _users
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.initial_values import InitialValue, validate_initial_values
from chatballs.integrations.adapters.registry import build_registry


class InitialValueContractTests(SimpleTestCase):
    def setUp(self):
        self.registry = build_registry(["chatballs.integrations.adapters.bitrix24"])
        self.operation = ADAPTER.operation("lead.create")

    def test_installed_create_bindings_are_typed_and_other_operations_have_none(self):
        for operation in ADAPTER.operations:
            self.assertEqual(validate_initial_values(operation, self.registry), [])
            self.assertEqual(bool(operation.initial_values), operation.key in {"lead.create", "contact.create"})

    def test_unknown_sources_targets_transforms_and_type_mismatches_are_rejected(self):
        for binding in (
            InitialValue("fields.NAME", "contact.password"),
            InitialValue("fields.UNKNOWN", "contact.name"),
            InitialValue("fields.NAME", "contact.name", "missing@1"),
            InitialValue("fields.NAME", "contact.phone", "list.of_object@1", {"key": "VALUE"}),
            InitialValue("fields.PHONE", "contact.phone", "list.of_object@1", {"key": 1}),
        ):
            with self.subTest(binding=binding):
                self.assertTrue(validate_initial_values(replace(self.operation, initial_values=(binding,)), self.registry))
        self.assertTrue(validate_initial_values(replace(self.operation, effect=Effect.UPDATE), self.registry))
        self.assertTrue(validate_initial_values(replace(self.operation,
            initial_values=self.operation.initial_values * 2), self.registry))


class BitrixUserLabelTests(SimpleTestCase):
    def test_full_name_then_email_then_id_without_changing_ids(self):
        rows = [
            {"ID": "001", "NAME": " Иван ", "SECOND_NAME": " Иванович ", "LAST_NAME": " Петров ", "EMAIL": "ignored@test.ru"},
            {"ID": 2, "NAME": " ", "SECOND_NAME": None, "LAST_NAME": "\t", "EMAIL": " staff@test.ru "},
            {"ID": "3", "NAME": None, "EMAIL": "  "},
            {"ID": 4, "SECOND_NAME": " Петрович ", "LAST_NAME": " Сидоров "},
            {}, None,
        ]
        self.assertEqual([(item.value, item.label) for item in _users(rows)], [
            ("001", "Иван Иванович Петров"), ("2", "staff@test.ru"),
            ("3", "3"), ("4", "Петрович Сидоров"),
        ])
