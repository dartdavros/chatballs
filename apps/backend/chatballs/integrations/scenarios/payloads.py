from chatballs.i18n import t


def issue_payload(issue):
    key = issue.code if issue.code in {"required", "type", "reference", "delegation"} else "structure"
    return {"path": issue.path, "code": issue.code, "message": t(f"scenarios.{key}")}


def scenario_payload(row, *, issues=None, detail=True):
    payload = {
        "id": str(row.public_id), "name": row.name, "revision": row.revision, "enabled": row.enabled,
        "origin": {"adapter": row.origin_adapter, "key": row.origin_key, "version": row.origin_version},
        "connections": list(row.connections.values_list("integration_id", flat=True)),
        "updatedAt": row.updated_at.isoformat(),
        "triggers": [trigger["kind"] for trigger in row.definition["triggers"]],
    }
    if detail:
        payload["definition"] = row.definition
    if issues is not None:
        payload["issues"] = [issue_payload(issue) for issue in issues]
    return payload
