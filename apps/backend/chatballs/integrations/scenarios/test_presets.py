from copy import deepcopy

from django.test import SimpleTestCase

from chatballs.integrations.adapters.template_labels import label_target
from chatballs.integrations.adapters.templates import ScenarioTemplate
from chatballs.integrations.scenarios.definition import empty_definition
from chatballs.integrations.scenarios.presets import canonical_document


class CompositePresetTests(SimpleTestCase):
    def test_full_document_is_copied_without_rewriting_literal_data(self):
        definition = empty_definition()
        guard = {"mode": "all", "items": [{"kind": "no_link", "connection": "self", "entity": "contact"}]}
        definition["conditions"] = deepcopy(guard)
        definition["triggers"] = [{"id": "event", "kind": "service", "connection": "self", "event": "changed"}]
        definition["steps"] = [{"id": "if", "kind": "if", "condition": guard, "then": [
            {"id": "try", "kind": "try", "body": [{"id": "parallel", "kind": "parallel", "branches": [[
                {"id": "loop", "kind": "foreach", "list": {"source": "parameter", "name": "rows"}, "body": [
                    {"id": "action", "kind": "action", "connection": "self", "target": "service:create", "inputs": {
                        "literal": {"source": "constant", "value": {"connection": "self", "name": "literal"}}}},
                    {"id": "wait", "kind": "wait", "mode": "event", "connection": "self", "event": "changed", "condition": deepcopy(guard)},
                ]}], [{"id": "call", "kind": "call", "scenario": "child", "inputs": {}}]]}], "catch": []}], "else": []}]
        definition["synchronization"] = [{"left": {"connection": "chatballs", "entity": "contact"}, "right": {"connection": "self", "entity": "contact"}}]
        before = deepcopy(definition)
        preset = ScenarioTemplate("composite", 1, "scenarios.title", "scenarios.title", definition=definition,
                                  labels=(("/steps/0/then/0/body/0/branches/0/0/body/0/name", "scenarios.title"),))
        copied = canonical_document(preset, 42)
        nested = copied["steps"][0]["then"][0]["body"][0]["branches"][0][0]["body"]
        self.assertEqual(nested[0]["connection"], "42")
        self.assertEqual(nested[0]["inputs"]["literal"]["value"]["connection"], "self")
        self.assertTrue(nested[0]["name"])
        self.assertEqual(nested[1]["condition"]["items"][0]["connection"], "42")
        self.assertEqual(copied["conditions"]["items"][0]["connection"], "42")
        self.assertEqual(copied["synchronization"][0]["right"]["connection"], "42")
        self.assertEqual(copied["triggers"][0]["connection"], "42")
        self.assertEqual(definition, before)

    def test_labels_cannot_replace_executable_fields_or_business_values(self):
        definition = empty_definition()
        definition["steps"] = [{"id": "a", "kind": "action", "target": "service:create", "inputs": {"name": "data"}}]
        for path in ("/steps/0/target", "/steps/0/inputs/name", "/steps/9/name", "/parameters/type"):
            with self.assertRaises(ValueError):
                label_target(definition, path)
