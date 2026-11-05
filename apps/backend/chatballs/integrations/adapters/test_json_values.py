"""Arbitrary JSON preserves drafts without creating references or capabilities."""

from datetime import datetime

from django.test import SimpleTestCase

from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import TypeSpec, validate_spec, validate_value
from chatballs.integrations.scenarios.bindings import BindingScope, check_binding
from chatballs.integrations.scenarios.definition import DefinitionContext
from chatballs.integrations.scenarios.types import compatible, read_type, write_type
from chatballs.integrations.scenarios.values import InvalidValues, RunValues, prepare_inputs


class JsonValueTests(SimpleTestCase):
    def test_mixed_values_and_literal_reference_names_round_trip(self):
        spec = TypeSpec("json", nullable=True)
        validate_spec(spec)
        self.assertEqual(read_type(write_type(spec)), spec)
        value = [None, "", True, 12, 1.25, ["line\none"], {"source": "step", "step": "private", "fileId": "ordinary-data"}]
        self.assertEqual(validate_value(spec, value), [])
        schema = TypeSpec("object", properties=(("example", spec),))
        binding = {"example": {"source": "constant", "value": value}}
        result = prepare_inputs(schema, binding, RunValues())
        self.assertEqual(result["example"], value)
        result["example"].append("changed")
        self.assertNotEqual(result["example"], value)
        issues = []
        check_binding(binding, TypeSpec("object", open=True),
            scope=BindingScope(TypeSpec("object")), context=DefinitionContext(),
            registry=default_registry(), path="inputs", issues=issues)
        self.assertEqual(issues, [])

    def test_non_json_and_non_nullable_values_are_rejected(self):
        spec = TypeSpec("json")
        cyclic = []
        cyclic.append(cyclic)
        for value in (None, {1: "key"}, (1, 2), float("nan"), {"x": float("inf")}, datetime.now(), cyclic):
            with self.subTest(value_type=type(value).__name__):
                self.assertTrue(validate_value(spec, value))

    def test_json_cannot_be_bound_as_a_file_or_other_concrete_type(self):
        spec = TypeSpec("json", nullable=True)
        self.assertTrue(compatible(TypeSpec("integer"), spec))
        self.assertFalse(compatible(spec, TypeSpec("string", nullable=True)))
        self.assertFalse(compatible(spec, TypeSpec("file", nullable=True)))
        schema = TypeSpec("object", properties=(("file", TypeSpec("file")),))
        with self.assertRaises(InvalidValues):
            prepare_inputs(schema, {"file": {"source": "constant", "value": {
                "fileId": "a776011e-af93-47ee-a86b-b887788081bc"}}}, RunValues())
