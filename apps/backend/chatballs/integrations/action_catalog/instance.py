"""Installation actions retain the domain's own global permission checks."""

from chatballs.identity import instance_commands, instance_email_commands, instance_tools_commands
from chatballs.integrations.action_catalog import instance_schemas as schema
from chatballs.integrations.action_catalog.administrative import register
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.contracts import Effect

for key, method, suffix, view, inputs, outputs, service, body, audit, execution, effect in (
    ("instance.settings.get", "GET", "settings/", "instance_views.InstanceAddressView", obj(), schema.OUTPUT, instance_commands.read, False, False, "local", Effect.READ),
    ("instance.settings.patch", "PATCH", "settings/", "instance_views.InstanceAddressView", schema.INPUT, schema.OUTPUT, instance_commands.update, True, False, "local", Effect.UPDATE),
    ("instance.email.check", "POST", "settings/email-check/", "instance_views.InstanceEmailCheckView", obj(email=schema.field("email")), obj(sent=schema.field("sent")), instance_email_commands.check, True, False, "io", Effect.CREATE),
    ("instance.network.get", "GET", "settings/tools-network/", "instance_tools_views.InstanceToolsNetworkView", obj(), schema.NETWORK, instance_tools_commands.read, False, False, "local", Effect.READ),
    ("instance.network.patch", "PATCH", "settings/tools-network/", "instance_tools_views.InstanceToolsNetworkView", obj(enabled=schema.field("enabled", "boolean", required=True)), schema.NETWORK, instance_tools_commands.update, True, True, "local", Effect.UPDATE),
):
    register(key=key, method=method, route=f"api/v1/instance/{suffix}", view=f"chatballs.identity.{view}",
        inputs=inputs, outputs=outputs, service=service, body=body, audit=audit, execution=execution, effect=effect)
