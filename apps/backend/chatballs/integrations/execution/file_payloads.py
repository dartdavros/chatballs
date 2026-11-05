"""Display names supplement file references without changing stored typed values."""

from uuid import UUID

from chatballs.integrations.scenario_state.files import ServiceFile


def _values(field, value):
    if not field or not isinstance(value, dict | list):
        return
    if isinstance(value, dict) and "redacted" in value:
        return
    if field["type"] == "file" and isinstance(value, dict):
        try:
            UUID(str(value.get("fileId")))
        except (ValueError, TypeError):
            return
        yield value
    elif field["type"] == "object" and isinstance(value, dict):
        for child in field.get("fields", []):
            yield from _values(child, value.get(child["name"]))
    elif field["type"] == "array" and isinstance(value, list):
        for child in value:
            yield from _values(field.get("items"), child)


def with_file_names(payload, run, secrets):
    from chatballs.integrations.execution.payloads import clean_value

    steps = [(step, [value for schema, key in (
        ("inputSchema", "arguments"), ("outputSchema", "result"),
    ) for value in _values(step.get(schema), step.get(key))]) for step in payload["steps"]]
    ids = {value["fileId"] for _step, values in steps for value in values}
    if not ids:
        return payload
    names = {str(row.public_id): clean_value(None, row.name, secrets) for row in ServiceFile.objects.filter(
        organization_id=run.organization_id, public_id__in=ids, execution_owners__step__run=run,
    )}
    for step, values in steps:
        step["fileNames"] = {value["fileId"]: names[value["fileId"]]
            for value in values if value["fileId"] in names}
    return payload
