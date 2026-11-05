"""One-time key issue/rotation; neither operation grants execution rights."""

import hashlib
import secrets

from chatballs.integrations.scenario_state.subscriptions import ScenarioExternalKey


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def key_payload(request, key, token=None):
    # Stable endpoint contract for T-172. No request is executed by the editor.
    path = f"/api/v1/scenario-triggers/{key.public_id}/"
    url = request.build_absolute_uri(path) if request is not None else path
    result = {"id": str(key.public_id), "trigger": key.trigger_id, "url": url}
    if token is not None and request is not None:
        result["key"] = token
    return result


def synchronize_keys(request, scenario):
    trigger_ids = [trigger["id"] for trigger in scenario.definition["triggers"] if trigger["kind"] == "api"]
    scenario.external_keys.exclude(trigger_id__in=trigger_ids).delete()
    result = []
    for trigger_id in trigger_ids:
        key = scenario.external_keys.filter(trigger_id=trigger_id).first()
        token = None
        if key is None:
            token = f"cbk_{secrets.token_urlsafe(32)}"
            key = ScenarioExternalKey.objects.create(organization_id=scenario.organization_id, scenario=scenario,
                trigger_id=trigger_id, token_hash=token_hash(token))
        result.append(key_payload(request, key, token))
    return result


def rotate_key(request, scenario, trigger_id):
    key = scenario.external_keys.select_for_update().get(trigger_id=trigger_id)
    token = f"cbk_{secrets.token_urlsafe(32)}"
    key.token_hash = token_hash(token)
    key.save(update_fields=["token_hash", "rotated_at"])
    return key_payload(request, key, token)
