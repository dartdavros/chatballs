"""Schemas and labels for aggregate results are derived from saved contracts."""

from chatballs.i18n import t
from chatballs.integrations.execution.contract_schemas import read_spec
from chatballs.integrations.scenarios.definition import DefinitionContext
from chatballs.integrations.scenarios.result_schemas import block_output
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.service_connections.payloads import field_payload


def context_for(run):
    definition = run.definition
    context = DefinitionContext()
    for key, saved in definition.get("contracts", {}).items():
        connection, _, target = key.partition(":")
        if "input" in saved:
            context.operations[connection, target] = read_spec(saved["input"]), read_spec(saved["output"])
    for key, saved in definition.get("graph", {}).items():
        context.scenarios[key] = read_type(saved["document"]["parameters"]), read_type(saved["document"]["results"])
    for key, saved in definition.get("events", {}).items():
        connection, _, event = key.partition(":")
        context.events[connection, event] = read_spec(saved)
    return context


def schema_and_names(run, block):
    from chatballs.integrations.execution.progress_payloads import TITLES
    from chatballs.integrations.execution.snapshots import walk
    context = context_for(run)
    spec = block_output(block, context)
    names = {}
    for child in walk([block]):
        saved = run.definition.get("contracts", {}).get(f"{child.get('connection')}:{child.get('target')}", {})
        names[child["id"]] = child.get("name") or t(saved.get("title_key") or TITLES.get(child["kind"], "runs.operation"))
    return spec, names


def label_schema(spec, names):
    payload = field_payload("", spec)
    labels = {"reason": "runs.block_errors", "step": "runs.operation", "service": "runs.service",
              "run": "runs.run_number", "number": "runs.item_index"}
    def visit(field):
        name = field["name"]
        if name in names:
            field["title"] = names[name]
        elif name in labels:
            field["title"] = t(labels[name])
        elif name.isdecimal():
            field["title"] = t("runs.branch_number", number=int(name) + 1)
        for child in field.get("fields", []):
            visit(child)
        if "items" in field:
            visit(field["items"])
    visit(payload)
    return payload


def display_errors(value, block):
    from copy import deepcopy

    from chatballs.integrations.execution.errors import error_message
    value = deepcopy(value)
    def entry(data, steps):
        if not isinstance(data, dict):
            return
        error = data.get("error")
        if isinstance(error, dict) and isinstance(error.get("reason"), str):
            error["reason"] = error_message(error["reason"])
        results = data.get("steps", {})
        for child in steps:
            if child["id"] in results:
                visit(results[child["id"]], child)

    def visit(data, current):
        if not isinstance(data, dict):
            return
        if current["kind"] == "foreach":
            for key in ("items", "errors"):
                for item in data.get(key, []):
                    entry(item, current.get("body", []))
        elif current["kind"] == "parallel":
            for index, steps in enumerate(current.get("branches", [])):
                entry(data.get("branches", {}).get(str(index)), steps)
    visit(value, block)
    return value
