"""Native grants permit only exact operations; original domain roles still apply."""

from chatballs.integrations.scenario_state.grants import ActionGrant


def organization_grants_cover(tenant, document):
    from chatballs.integrations.execution.snapshots import walk
    blocks = list(walk(document["steps"]))
    # A parent's grant must not implicitly authorize an unknown child graph or
    # a service operation. Each child is checked by the existing chain policy.
    if any(block["kind"] == "call" for block in blocks):
        return False
    actions = [block for block in blocks if block["kind"] == "action"]
    if not actions or any(block.get("connection") != "chatballs"
            or not block.get("target", "").startswith("chatballs:") for block in actions):
        return False
    keys = {block["target"].removeprefix("chatballs:") for block in actions}
    granted = set(ActionGrant.objects.filter(organization_id=tenant.organization_id,
        membership=tenant.membership, integration__isnull=True, operation_key="",
        enabled=True, scope="organization", native_key__in=keys).values_list("native_key", flat=True))
    return keys <= granted
