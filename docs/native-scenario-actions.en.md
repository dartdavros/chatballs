# Managing scenarios from scenarios

`scenarios.*` provide listing, reading, creation, update, deletion, validation,
copying, preset installation and the editor catalog. Creation and updates accept
`settings: {definition, agentPolicies}`. The trusted `scenario_settings@1`
control composes the existing editor sections and drawers, preserving the
selected AI agent together with its policy. Product services enforce
`integrations.manage`, current update/delete revisions and supported trigger
sources. Saving a definition is not a manual launch.

Definition arguments are fully hidden in the journal. Reading a definition
removes secret values according to its step schemas; unknown schemas do not
expose inputs. This safe projection is not a credential backup.
`scenarios.copy.post` copies the stored definition on the server. External keys
are metadata only; issuing a one-time credential remains an interactive protocol.

`agents.actions.get/put` read and change exact AI action policies. Updates check
all revisions, `ai.manage` and the current delegate atomically. A stale item
rolls back the batch. `synchronization.get/put` retain product validation for
pairs, directions, transforms, links and adapter capabilities. An adapter without
conditional remote writes cannot bypass that restriction. Compound values use
the shared field editor.

`runs.get`, `runs.detail.get`, `runs.actions.get` return the visible journal,
details and launch catalog. `runs.lookup.get` and `runs.approval_lookup.get`
check context and declared lookup schemas; the latter also checks the approver
and frozen contract. Approval edit-lease tokens are never ordinary action
outputs. `runs.control.post` supports cancellation and reconciliation only.
Cancellation does not establish the outcome of an already sent effect.
`runs.retention.get/put` retain OWNER/ADMIN restrictions, revisions, explicit
shortening confirmation and the 24-hour cleanup delay.

`entity_links.get`, `entity_links.search.get`, `entity_links.command.post`
operate on the canonical visible conversation. Replacement requires a candidate
from the completed matching search and the current link revision. Unlinking is
explicit. Phone and email do not implicitly create a link.

Example: read `scenarios.detail.get`, validate your own complete configuration
with `scenarios.check.post`, then call `scenarios.detail.put` with the observed
revision. Use `scenarios.copy.post` for an exact copy retaining stored secrets.
Another example: read `agents.actions.get`, select one action and send its `id`,
`ask` mode and current `revision` through `agents.actions.put`. Writes retain
the common step confirmation policy.

Launch/preview, approval and parameter editing, intentional repeat, wait and
conflict decisions remain digest/revision-bound runner protocols. Inventory
records these explicitly; management wrappers cannot mint a fresh launch
principal. Nested scenarios use the call block and intersect every ancestor's
restrictions. External record search invokes the registered adapter operation
through the common runner; candidate reads and link changes have native actions.

Global profiles, personal sessions, installation, platform and initial setup
are registered in the same catalog, but are unavailable to organization scenarios
and AI. Registration grants no execution authority. Profile commands act on the
current user; session management requires that user's valid session. Installation
settings retain their separate administrator permission, while provisioning
requires a valid platform token. Login, passwords, TOTP and invitation acceptance
retain their identification protocols.

Administrative operations use the existing application settings and platform API.
Organization automation cannot access SMTP, storage, installation updates or
global profiles even when its delegate personally holds those permissions.
Organization settings actions remain available in the editor.
Developer contract and examples: [global actions](native-global-actions.md).
