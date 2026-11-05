"""Connection output excludes credentials before durable effect receipts."""

from chatballs.ai.diagnostic_redaction import (
    DiagnosticRedactor,
    integration_secrets,
    is_sensitive_key,
)
from chatballs.ai.pseudonymization import Pseudonymizer
from chatballs.integrations.models import Integration


def safe_output(context, payload):
    secrets = integration_secrets(Integration.objects.filter(organization_id=context.organization_id))
    redactor = DiagnosticRedactor(Pseudonymizer(), secrets)
    for row in payload.get("items", []) if "items" in payload else [payload.get("integration", {})]:
        if "lastError" in row:
            row["lastError"] = redactor.text(row["lastError"])
        for key in ("baseUrl", "proxyUrl"):
            config = row.get("config", {})
            if config.get(key):
                config[key] = redactor.text(config[key])
        external = row.get("externalServer", {})
        if external.get("url"):
            external["url"] = redactor.text(external["url"])
        for header in external.get("headers", []):
            if header.get("secret") or is_sensitive_key(header.get("name", "")):
                header["value"] = ""
        for tool in external.get("tools", []):
            tool["inputSchema"] = redactor.clean(tool.get("inputSchema", {}))
            for key in ("description", "title"):
                tool[key] = redactor.text(tool.get(key, ""))
    return payload
