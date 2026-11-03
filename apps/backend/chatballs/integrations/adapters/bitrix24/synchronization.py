"""Read projection for exchange; REST update does not advertise conditional CAS."""

import hashlib
import json

from django.utils.dateparse import parse_datetime

from chatballs.integrations.adapters.bitrix24.operations import entity_fields
from chatballs.integrations.adapters.synchronization import EntitySnapshot, SynchronizationBinding


def binding(entity):
    def arguments(identity):
        if not identity.isdecimal() or int(identity) < 1:
            raise ValueError("invalid_identity")
        return {"id": int(identity)}
    def snapshot(value):
        if not isinstance(value, dict) or not value.get("DATE_MODIFY"):
            # Not-found/permission failures are not invented deletion evidence.
            raise ValueError("record_version_unavailable")
        at = parse_datetime(value["DATE_MODIFY"])
        selected = {name: value[name] for name, _ in entity_fields(entity).properties if name in value}
        version = hashlib.sha256(json.dumps({"at": value["DATE_MODIFY"], "values": selected}, sort_keys=True).encode()).hexdigest()
        return EntitySnapshot(selected, version, at)
    return SynchronizationBinding(f"{entity}.get", arguments, snapshot)
