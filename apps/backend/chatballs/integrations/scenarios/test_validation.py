from copy import deepcopy

from django.test import SimpleTestCase

from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.scenarios.definition import DefinitionContext, empty_definition
from chatballs.integrations.scenarios.validation import validate_definition

TEXT = TypeSpec("string", required=True)
INPUT = TypeSpec("object", properties=(("name", TEXT),))
OUTPUT = TypeSpec("object", properties=(("name", TEXT), ("rows", TypeSpec("array", items=INPUT))))


def constant(value):
    return {"source": "constant", "value": value}


def action(identifier="a", value=None):
    return {"id": identifier, "kind": "action", "connection": "1", "target": "service:create",
            "inputs": {"name": value or constant("Example")}}


class DefinitionValidationTests(SimpleTestCase):
    def setUp(self):
        self.context = DefinitionContext(
            operations={("1", "service:create"): (INPUT, OUTPUT)}, connections={"1"},
            scenarios={"child": (INPUT, OUTPUT)}, context=INPUT,
            events={("1", "created"): OUTPUT},
        )
        self.document = empty_definition()
        self.document["steps"] = [action()]

    def issues(self):
        return validate_definition(self.document, context=self.context)

    def test_all_blocks_and_lexical_sources_in_one_document(self):
        self.document["parameters"] = {"type": "object", "properties": {"name": {"type": "string", "required": True}}}
        self.document["steps"] = [
            action(value={"source": "parameter", "name": "name"}),
            {"id": "branch", "kind": "if", "condition": {"mode": "all", "items": [
                {"left": {"source": "step", "step": "a", "path": "name"}, "op": "filled"}]},
             "then": [action("yes")], "else": [action("no")]},
            {"id": "each", "kind": "foreach", "list": {"source": "step", "step": "a", "path": "rows"},
             "body": [action("item", {"source": "item", "step": "each", "path": "name"})]},
            {"id": "parallel", "kind": "parallel", "branches": [[action("left")], [action("right")]]},
            {"id": "try", "kind": "try", "body": [action("attempt")],
             "catch": [action("catch", {"source": "error", "step": "try", "path": "reason"})]},
            {"id": "wait", "kind": "wait", "mode": "duration", "duration": 60},
            {"id": "call", "kind": "call", "scenario": "child", "inputs": {"name": constant("Child")}},
        ]
        self.assertEqual(self.issues(), [])

    def test_future_and_sibling_branch_results_are_not_in_scope(self):
        self.document["steps"] = [
            {"id": "parallel", "kind": "parallel", "branches": [
                [action("left")], [action("right", {"source": "step", "step": "left", "path": "name"})]]},
            action("after", {"source": "step", "step": "left", "path": "name"}),
        ]
        self.assertEqual([issue.code for issue in self.issues()], ["reference", "reference"])
        self.document["steps"] = [action("first", {"source": "step", "step": "future", "path": "name"}), action("future")]
        self.assertEqual(self.issues()[0].code, "reference")

    def test_empty_required_constants_and_child_inputs_block_enable(self):
        self.document["steps"] = [action(value=constant("  ")),
            {"id": "call", "kind": "call", "scenario": "child", "inputs": {"name": constant("")}}]
        self.assertEqual([issue.code for issue in self.issues()], ["required", "required"])

    def test_unknown_fields_types_and_executable_payloads_are_invalid(self):
        self.document["steps"][0]["inputs"]["name"] = {"source": "python", "code": "print('unsafe')"}
        self.assertTrue(self.issues())
        self.document["steps"] = [action(value=constant(10))]
        self.assertEqual(self.issues()[0].code, "type")
        self.document["tenant"] = 2
        self.assertEqual(self.issues()[0].code, "structure")

    def test_transforms_are_registered_and_type_checked(self):
        self.document["steps"] = [action(value={**constant(" trim "), "transform": "text.trim@1"})]
        self.assertEqual(self.issues(), [])
        self.document["steps"][0]["inputs"]["name"]["transform"] = "unknown@1"
        self.assertEqual(self.issues()[0].code, "type")

    def test_files_are_tenant_references_and_nested_types_are_preserved(self):
        self.context.operations["1", "service:create"] = (TypeSpec("object", properties=(
            ("file", TypeSpec("file", required=True)),)), OUTPUT)
        file_id = "fba25493-414e-4bf2-8b6e-f889b7baf339"
        self.document["steps"][0]["inputs"] = {"file": constant({"fileId": file_id})}
        self.assertEqual(self.issues()[0].code, "reference")
        self.context.files.add(file_id)
        self.assertEqual(self.issues(), [])

    def test_every_trigger_and_schedule_policy(self):
        for kind in ("staff", "ai", "scenario", "api", "service"):
            trigger = {"id": kind, "kind": kind}
            if kind == "service":
                trigger.update(connection="1", event="created")
            self.document["triggers"] = [trigger]
            self.document["access"]["delegated"] = True
            self.assertEqual(self.issues(), [], kind)
        self.document["triggers"] = [{"id": "schedule", "kind": "schedule", "timezone": "Europe/Moscow",
            "days": [0, 2], "time": "09:00", "misfire": "once", "ambiguous": "first", "nonexistent": "skip"}]
        self.assertEqual(self.issues(), [])
        self.document["access"]["delegated"] = False
        self.assertEqual(self.issues()[0].code, "delegation")
        self.document["triggers"][0]["timezone"] = "Not/AZone"
        self.assertEqual(self.issues()[0].code, "schedule")

    def test_no_reference_to_context_not_supplied_by_server(self):
        for path in ("credentials", "organization.id", "user.role", "unknown"):
            self.document["steps"] = [action(value={"source": "context", "path": path})]
            self.assertEqual(self.issues()[0].code, "reference")

    def test_event_bindings_must_be_valid_for_every_launch(self):
        self.document["triggers"] = [{"id": "event", "kind": "service", "connection": "1", "event": "created"}]
        self.document["access"]["delegated"] = True
        self.document["steps"] = [action(value={"source": "event", "path": "name"})]
        self.assertEqual(self.issues(), [])
        self.document["triggers"].append({"id": "staff", "kind": "staff"})
        self.assertEqual(self.issues()[0].code, "reference")

    def test_format_does_not_mutate_during_validation(self):
        original = deepcopy(self.document)
        self.assertEqual(self.issues(), [])
        self.assertEqual(self.document, original)

    def test_step_outcome_is_typed_and_lexically_scoped(self):
        predicate = {"left": {"source": "step", "step": "a", "aspect": "state"}, "op": "eq", "right": constant("failed")}
        branch = {"id": "branch", "kind": "if", "condition": {"mode": "all", "items": [predicate]}, "then": [], "else": []}
        self.document["steps"] = [action(), branch]
        self.assertEqual(self.issues(), [])
        predicate["right"] = constant("unknown")
        self.assertTrue(self.issues())
        predicate["right"] = constant("completed")
        self.document["steps"] = [branch, action()]
        self.assertTrue(self.issues())
        self.document["steps"] = [{"id": "parallel", "kind": "parallel", "branches": [[action()], [branch]]}]
        self.assertTrue(self.issues())

    def test_label_and_channel_predicates_use_tenant_catalogs(self):
        self.context.labels.add(7)
        self.context.channels.add(8)
        self.document["conditions"]["items"] = [
            {"kind": "tag", "tag": 7, "scope": "conversation", "present": False},
            {"kind": "channel", "connection": 8, "present": True},
            {"kind": "context_present", "path": "name", "present": False},
        ]
        self.assertEqual(self.issues(), [])
        self.document["conditions"]["items"][0]["tag"] = 9
        self.document["conditions"]["items"][1]["connection"] = 10
        self.assertEqual([issue.code for issue in self.issues()], ["reference", "reference"])

    def test_native_link_connections_are_tenant_references_not_plain_integers(self):
        from chatballs.integrations.action_catalog.registry import action_schemas
        from chatballs.integrations.scenarios.catalog import connection_ids
        link = next(action for action in action_schemas() if action.key == "entity_link.create")
        self.context.operations["chatballs", "chatballs:entity_link.create"] = (link.input, link.output)
        self.context.entities["1", "contact"] = INPUT
        self.document["steps"] = [{"id": "link", "kind": "action", "connection": "chatballs", "target": "chatballs:entity_link.create",
            "inputs": {"connection": constant(1), "entity": constant("contact"), "external_id": constant("123")}}]
        self.assertEqual(self.issues(), [])
        self.assertEqual(connection_ids(self.document), {1})
        self.document["steps"][0]["inputs"]["connection"] = constant(999)
        self.assertEqual(self.issues()[0].code, "reference")

    def test_identifiers_and_presentation_metadata_cannot_break_storage_or_controls(self):
        for identifier in ("x" * 101, "a/b", "", {"id": "a"}):
            self.document["triggers"][0]["id"] = identifier
            self.assertTrue(any(issue.code == "identifier" for issue in self.issues()))
        self.document["triggers"][0]["id"] = "staff"
        self.document["steps"][0]["name"] = {"unsafe": "presentation"}
        self.assertEqual(self.issues()[0].code, "structure")
        self.document["steps"][0].pop("name")
        self.document["parameters"]["title"] = ["not text"]
        self.assertEqual(self.issues()[0].code, "schema")

    def test_required_nullable_and_scalar_to_record_list_keep_their_type_semantics(self):
        self.context.operations["1", "service:create"] = (TypeSpec("object", properties=(("name", TypeSpec("string", required=True, nullable=True)),)), OUTPUT)
        self.document["steps"] = [action(value=constant(None))]
        self.assertEqual(self.issues(), [])
        self.context.context = TypeSpec("object", properties=(("phone", TypeSpec("string")),))
        self.context.operations["1", "service:create"] = (TypeSpec("object", properties=(("phones", TypeSpec("array", items=TypeSpec("object", properties=(("VALUE", TEXT),)))),)), OUTPUT)
        self.document["steps"][0]["inputs"] = {"phones": {"source": "context", "path": "phone", "transform": "list.of_object@1", "args": {"key": "VALUE"}}}
        self.assertEqual(self.issues(), [])
