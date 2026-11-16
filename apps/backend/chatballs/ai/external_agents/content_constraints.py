"""The declared intersection of native transport and the executor's capabilities."""

from chatballs.ai.external_agents.payloads import open_payload
from chatballs.conversations.attachment_policy import MAX_FILE_BYTES
from chatballs.integrations.models import Integration


def constraints(row):
    route = open_payload(row.seed_ciphertext)["route"]
    transport = None if row.conversation.is_test else Integration.objects.get(pk=route["connectionId"])
    types = ["text", "file", "image", "contact_request", "formatted"]
    supported = row.session.connection.capabilities.get("directions", {}).get("toChatballs", [])
    maximum = {"TELEGRAM": 4096, "MAX": 4000, "VK": 4000}.get(transport.provider if transport else None)
    return {"types": [kind for kind in types if kind in supported],
            "maxFileBytes": MAX_FILE_BYTES, "maxTextCharacters": maximum}


def check_text(text, row, *, caption=False):
    limit = constraints(row)["maxTextCharacters"]
    if caption:
        route = open_payload(row.seed_ciphertext)["route"]
        provider = None if row.conversation.is_test else Integration.objects.get(pk=route["connectionId"]).provider
        limit = 1024 if provider == "TELEGRAM" else 4000
    if limit is not None and len(text) > limit:
        raise ValueError("channel_restricted")
