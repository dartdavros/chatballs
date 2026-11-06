from chatballs.i18n import t


def issue_payload(issue):
    key = "required" if issue.code == "null" else issue.code if issue.code in {"required", "type", "reference", "delegation"} else "structure"
    return {"path": issue.path, "code": issue.code, "message": t(f"scenarios.{key}")}


def scenario_payload(row, *, issues=None, detail=True):
    from chatballs.integrations.execution.errors import error_message
    from chatballs.integrations.scenario_state.automation import EventDelivery
    delivery = EventDelivery.objects.filter(scenario=row).order_by("-pk").first()
    error = delivery.error_code if delivery and delivery.state in {"failed", "pending"} else ""
    if not error:
        error = row.schedules.exclude(error_code="").values_list("error_code", flat=True).first() or ""
    document = row.definition
    payload = {
        "id": str(row.public_id), "name": row.name, "revision": row.revision, "enabled": row.enabled,
        "origin": {"adapter": row.origin_adapter, "key": row.origin_key, "version": row.origin_version},
        "connections": list(row.connections.values_list("integration_id", flat=True)),
        "updatedAt": row.updated_at.isoformat(),
        "triggers": [trigger["kind"] for trigger in document["triggers"]],
        "nativeEvents": [trigger["event"] for trigger in document["triggers"] if trigger["kind"] == "chatballs"],
        "accessScope": document["access"]["scope"],
        "automationError": error_message(error) if error else "",
    }
    if detail:
        payload["definition"] = document
        from chatballs.integrations.execution.scenario_agent_policies import (
            payload as agent_policies,
        )
        payload["agentPolicies"] = agent_policies(row)
    if issues is not None:
        payload["issues"] = [issue_payload(issue) for issue in issues]
    return payload
