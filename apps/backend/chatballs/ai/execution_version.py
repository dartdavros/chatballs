"""A configuration fingerprint detects changes even in update_fields writes."""

import hashlib
import json


def configuration_version(agent):
    if agent is None:
        return ""
    fields = ("pk", "channel_id", "provider_integration_id", "model", "model_params", "status",
              "persona", "tone", "instructions", "answer_language")
    return hashlib.sha256(json.dumps({key: getattr(agent, key) for key in fields},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
