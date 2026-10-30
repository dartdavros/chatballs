from django.test import SimpleTestCase

from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.scenarios.values import InvalidValues, RunValues, prepare_inputs


class ActualInputTests(SimpleTestCase):
    def test_step_outcome_requires_an_actual_recorded_outcome(self):
        from chatballs.integrations.scenarios.bindings import STEP_STATE_TYPE
        schema = TypeSpec("object", properties=(("outcome", STEP_STATE_TYPE),))
        bindings = {"outcome": {"source": "step", "step": "a", "aspect": "state"}}
        self.assertEqual(prepare_inputs(schema, bindings, RunValues(states={"a": "failed"})), {"outcome": "failed"})
        for states in ({}, {"a": "unknown"}):
            with self.assertRaises(InvalidValues):
                prepare_inputs(schema, bindings, RunValues(states=states))

    def test_actual_values_are_checked_before_the_effect_boundary(self):
        schema = TypeSpec("object", properties=(("name", TypeSpec("string", required=True)),))
        bindings = {"name": {"source": "step", "step": "search", "path": "name", "transform": "text.trim@1"}}
        for steps in ({}, {"search": {"name": "   "}}, {"search": {"name": 1}}):
            with self.assertRaises(InvalidValues):
                prepare_inputs(schema, bindings, RunValues(steps=steps))
        self.assertEqual(prepare_inputs(schema, bindings, RunValues(steps={"search": {"name": " Anna "}})), {"name": "Anna"})

    def test_structured_values_and_tenant_files(self):
        file_id = "a776011e-af93-47ee-a86b-b887788081bc"
        schema = TypeSpec("object", properties=(("file", TypeSpec("file", required=True)), ("source", TypeSpec("string", required=True))))
        bindings = {"file": {"source": "parameter", "name": "file"}, "source": {"source": "constant", "value": "employee"}}
        values = RunValues(parameters={"file": {"fileId": file_id}})
        with self.assertRaises(InvalidValues):
            prepare_inputs(schema, bindings, values)
        values.files.add(file_id)
        self.assertEqual(prepare_inputs(schema, bindings, values), {"file": {"fileId": file_id}, "source": "employee"})

    def test_external_payload_field_is_not_reinterpreted_as_an_organization_file(self):
        schema = TypeSpec("object", properties=(("payload", TypeSpec("object", open=True)),))
        bindings = {"payload": {"source": "constant", "value": {"fileId": "external-record"}}}
        result = prepare_inputs(schema, bindings, RunValues())
        self.assertEqual(result, {"payload": {"fileId": "external-record"}})
        result["payload"]["fileId"] = "changed"
        self.assertEqual(bindings["payload"]["value"]["fileId"], "external-record")
