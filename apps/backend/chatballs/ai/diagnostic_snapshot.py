"""Capture the actual turn configuration, without calling tools or the provider."""

from django.conf import settings
from django.utils import timezone

from chatballs.ai.diagnostic_redaction import DiagnosticRedactor, integration_secrets
from chatballs.ai.tool_bindings import conversation_client_data
from chatballs.integrations.models import Integration, IntegrationKind
from chatballs.integrations.read_only import server_tools


def diagnostic_context(agent, conversation, pseudonymizer, client=None):
    client = client if client is not None else conversation_client_data(conversation)
    servers = list(Integration.objects.filter(
        organization_id=agent.organization_id, kind=IntegrationKind.EXTERNAL_SERVER
    ).order_by("id"))
    integrations = [*servers]
    if agent.provider_integration is not None:
        integrations.append(agent.provider_integration)
    if conversation is not None and conversation.connection is not None:
        integrations.append(conversation.connection)
    secrets = integration_secrets(integrations)
    secrets.extend(str(value) for fields in client.web_fields.values() for value in fields.values())
    redactor = DiagnosticRedactor(pseudonymizer, secrets)
    enabled = set(agent.tools.values_list("integration_id", "tool_name"))
    unselected = [
        {"integrationId": server.id, "name": tool.name, "reason": "not_enabled_for_agent"}
        for server in servers for tool in server_tools(server)
        if (server.id, tool.key) not in enabled
    ]
    snapshot = {
        "schemaVersion": 1,
        "version": settings.CHATBALLS_VERSION,
        "capturedAt": timezone.now().isoformat(),
        "agent": {"id": agent.id, "name": agent.name, "model": agent.model,
                  "historyLimit": agent.history_limit, "status": agent.status},
        "providerIntegrationId": agent.provider_integration_id,
        "connectionId": conversation.connection_id if conversation else None,
        "integrations": [
            {"id": server.id, "name": server.name, "provider": server.provider,
             "active": server.is_active, "revision": server.runtime_revision,
             "urlTemplate": redactor.url(str(server.config.get("url", ""))),
             "parameters": [
                 {key: item.get(key) for key in ("name", "type", "required", "location", "source")}
                 for item in server.config.get("parameters", [])
             ]}
            for server in servers
        ],
        "toolAvailability": unselected,
    }
    return client, redactor, snapshot
