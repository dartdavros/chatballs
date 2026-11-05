"""Only executable descriptors may satisfy a product API entry."""

from django.test import SimpleTestCase

from chatballs.i18n.messages import CATALOG
from chatballs.integrations.action_catalog.coverage import (
    entry_key,
    inventory,
    mounted_entries,
    problems,
)
from chatballs.integrations.action_catalog.registry import native_actions
from chatballs.integrations.adapters.registry import default_registry


class NativeCoverageTests(SimpleTestCase):
    def test_every_product_entry_has_an_executable_exact_action(self):
        self.assertEqual(problems(), [])

    def test_inventory_resolves_real_routes_and_method_inheritance(self):
        expected = {entry_key(row) for row in inventory()}
        self.assertEqual(mounted_entries(), expected)
        self.assertEqual(len(expected), len(inventory()), "Duplicate inventory entries")
        excluded = [row for row in inventory() if row["action"] is None]
        self.assertTrue(excluded)
        self.assertTrue(all(row["reason"] for row in excluded))

    def test_executable_actions_have_translated_titles_and_named_inputs(self):
        missing = set()
        def translated(key):
            for language in ("ru", "en"):
                if key not in CATALOG[language]:
                    missing.add(f"{language}:{key}")
                else:
                    self.assertNotIn("??", CATALOG[language][key], f"{language}:{key}")
        def fields(spec):
            if spec.control:
                control = default_registry().extension("control", spec.control)
                self.assertIsNotNone(control, spec.control)
                self.assertIn(spec.type, control.implementation.types, spec.control)
            for key in (spec.hint_key, spec.placeholder_key, spec.pattern_error_key):
                if key:
                    translated(key)
            for option in spec.options:
                translated(option.label_key)
            for _name, child in spec.properties:
                self.assertTrue(child.title_key)
                translated(child.title_key)
                fields(child)
            if spec.items:
                fields(spec.items)
        for action in native_actions(authority=None):
            translated(action.operation.title_key)
            self.assertFalse(action.operation.input.open, action.key)
            self.assertTrue(callable(action.execute), action.key)
            fields(action.operation.input)
            fields(action.operation.output)
        self.assertEqual(sorted(missing), [])
