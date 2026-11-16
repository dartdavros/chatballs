"""A configuration fingerprint detects changes even in update_fields writes."""

import hashlib
import json


def configuration_version(agent):
    if agent is None:
        return ""
    fields = ("pk", "channel_id", "provider_integration_id", "model", "model_params", "status",
              "persona", "tone", "instructions", "answer_language")
    values = {key: getattr(agent, key) for key in fields}
    # Preserve the deployed fingerprint of every untouched builtin agent.
    if agent.execution_mode != "builtin" or agent.execution_version != 1:
        values.update(executionMode=agent.execution_mode, executionVersion=agent.execution_version)
    return hashlib.sha256(json.dumps(values,
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
