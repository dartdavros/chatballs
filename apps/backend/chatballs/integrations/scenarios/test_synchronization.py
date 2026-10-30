from copy import deepcopy

from django.test import SimpleTestCase

from chatballs.integrations.adapters.schema import EnumOption, TypeSpec
from chatballs.integrations.scenarios.definition import DefinitionContext
from chatballs.integrations.scenarios.synchronization import check_synchronization


class SynchronizationDefinitionTests(SimpleTestCase):
    def test_directional_status_maps_are_independent_and_missing_values_preserve_target(self):
        status = TypeSpec("enum", options=(EnumOption("open", ""), EnumOption("closed", "")))
        stage = TypeSpec("enum", options=(EnumOption("work", ""), EnumOption("won", "")))
        context = DefinitionContext(entities={("chatballs", "dialog"): TypeSpec("object", properties=(("status", status),)),
            ("1", "record"): TypeSpec("object", properties=(("stage", stage),))},
            writable_fields={("chatballs", "dialog"): {"status"}, ("1", "record"): {"stage"}})
        pair = {"id": "p", "enabled": True, "left": {"connection": "chatballs", "entity": "dialog"}, "right": {"connection": "1", "entity": "record"},
            "direction": "both", "sourceOfTruth": "left", "conflict": "source", "deletion": "unlink",
            "causality": {"suppressEcho": True, "requireExplicitLink": True}, "fields": [
                {"left": "status", "right": "stage", "direction": "forward", "values": [{"from": "open", "to": "work"}, {"from": "closed", "to": None}]},
                {"left": "status", "right": "stage", "direction": "reverse", "values": [{"from": "work", "to": "closed"}]}]}
        original = deepcopy(pair)
        issues = []
        check_synchronization([pair], context=context, issues=issues)
        self.assertEqual(issues, [])
        self.assertEqual(pair, original)
        pair["fields"][1]["values"][0]["to"] = "unknown"
        check_synchronization([pair], context=context, issues=issues)
        self.assertTrue(issues)
        pair["causality"]["requireExplicitLink"] = False
        issues = []
        check_synchronization([pair], context=context, issues=issues)
        self.assertIn("policy", [issue.code for issue in issues])
