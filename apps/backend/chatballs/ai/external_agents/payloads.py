"""Recovery payloads never appear in JSON diagnostics or outbox jobs."""

from chatballs.ai.external_agents.json_payloads import dumps, loads
from chatballs.identity.crypto import decrypt_secret, encrypt_secret


def seal(value):
    return encrypt_secret(dumps(value))


def open_payload(value):
    return loads(decrypt_secret(value))


def utc(value):
    return value.isoformat().replace("+00:00", "Z")
