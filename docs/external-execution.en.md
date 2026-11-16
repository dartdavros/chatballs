# External agent execution

The feature is off by default. An owner or administrator manages it in
**Settings → Maintenance → External execution**, separately from business integrations.
Installation files do not need editing.

## Setup

1. Enable the feature and enter the service name, HTTPS address and outgoing key.
2. Save the connection. Saving neither calls the service nor creates an incoming key.
   “Check connection” is a separate access and compatibility check.
3. Create the key that permits the service to access Chatballs. Its full value is
   shown once. Explicit replacement or revocation invalidates the old access.
4. Bind a Chatballs agent to its identifier in the service. Set time limits and
   permissions for fields and templates. Initiative requires a separate permission.
5. Save the permissions and select the configured executor on the agent card.
   Use the card’s regular AI control to start customer responses.

Under “Processing and waiting”, choose “Normal request” or “Long processing” in
“Processing mode”. New requests use the corresponding configured duration, within
the maximum wait. Editing this setting does not extend an existing request’s
deadline; retries and progress messages do not extend it either.

The agent card does not duplicate the connection form. Builtin instructions,
model, knowledge, skills, actions and tools remain saved. The response language is
sent as a preference; it does not change the external model. Speech recognition
is configured separately in Chatballs. The executor receives the transcript, never
the original recording. Employee assistance uses its own Chatballs provider settings.

## Permissions and consent

Standard fields, custom fields and formatted templates initially have no grants.
Empty lists allow ordinary text responses when the executor is ready. A custom
grant identifies both its WEB source and field definition. Matching names or keys
never merge permissions. Changed or unavailable definitions need review; recreated
fields and templates do not inherit previous access. Template previews use a saved
example belonging to that organization’s template.

WEB conversations require current customer consent. Chatballs retains the
organization’s main consent text and appends disclosure naming the configured
service, original message text and permitted fields. The server determines the
revision; previous consent cannot authorize a changed revision.

## Testing and stopping

The test chat sends a real request that may trigger service actions. There is no
simulation. This is disclosed before sending. Only explicitly permitted test fields
can be entered; real customer records and other conversations are not substituted.
The private test belongs to its initiating owner or administrator and stays outside
the customer inbox and employee queue. Restarting, closing or changing admission
revokes the previous test scope’s authority.

Waiting, handoff and unknown or partial delivery show actual state. An uncertain
delivery gets no success mark or blind retry. Internal explanations are not sent
to customers.

Disabling the feature stops further external operations while retaining settings
and the agent’s selected execution mode. It never switches to builtin replies
automatically. Re-enabling requires a connection check and explicit confirmation
of bindings and permissions. The API also enforces disabled and unready states.

This describes the Chatballs implementation. See the [T-192 local verification
report](verification/T-192/README.md) for checks performed. External service,
STT/LLM and channel acceptance, production deployment and release publication are
not claimed.
