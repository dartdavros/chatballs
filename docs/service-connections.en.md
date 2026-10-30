# Connecting services

Open integration settings and select Services. The catalog lists packages
installed by your installation administrator. You can connect the same service
more than once; use different names to distinguish connections.

## Bitrix24

1. Create an inbound webhook in your Bitrix24 portal.
2. Grant CRM access. The preset's assignee selection also requires access to users.
3. Choose Connect in the catalog, enter a connection name and paste the webhook URL.
4. Choose Check and connect. The check reads webhook permissions; it does not
   create or change leads, contacts or deals.

Treat the webhook URL as a password. After saving, the connection card shows the
portal host and access status, not the secret URL. If verification fails, check
the URL and the webhook's permissions, then retry.

See [Bitrix24's setup instructions](https://apidocs.bitrix24.com/first-steps/first-rest-api-call.html)
for webhook creation and permission selection.

## Connection card

Use the card to rename the connection, check access or replace credentials.
Restore revoked or expired access through the card's recovery action. Checking
access does not execute a preset.

Pause prevents new connection operations while preserving settings. Choose
Resume to restore them. Deleting a connection does not delete data in the
external service; read the application's confirmation first.

## Presets

After connecting, the card lists the installed package's presets. Bitrix24
provides Create a lead from a conversation. It requires the connection, CRM and
user permissions, an assignee and a stage. Its definition creates a lead from
contact data and saves the conversation's link to that lead.

Configure creates an editable organization copy in the common
[scenario editor](scenarios.en.md). Save it disabled, add steps and explicitly
enable it after validation. Execution is delivered by dependent tasks.
Saving access never enables scenarios automatically.

Existing external HTTP/MCP servers retain their tab. You do not need to reconnect
them or alter read-only confirmations to use the new Services tab.
