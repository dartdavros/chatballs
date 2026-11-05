# Organization and knowledge actions

This document describes the T-175 action groups connected in the source tree.
The remaining organization and connection catalog is still being developed;
see the [verification log](verification/T-175/README.md) for checked results.

Select actions in the common scenario editor. Fields, transformations,
confirmations and results use the same forms as
[communication and service actions](native-service-actions.en.md).

## Employees and availability

Actions cover employee lists, details and photos, creation, profile, role and
group updates, blocking and unblocking, session revocation, access recovery by
email, ownership transfer, and invitation resend and revocation. Adding an
existing global account sends an invitation; membership starts after the person
accepts it.

Automation preserves ordinary employee governance. The owner cannot be blocked;
only the owner can transfer ownership. An organization cannot reset the password
of an employee who also belongs to another organization. A privileged-action
refusal remains in the audit log and fails the step.

Creation and access recovery use the existing email workflow. Passwords never
become step results, downstream bindings, journal fields or stored receipt data.
One-time password display remains in the ordinary access-management form.
A completed step confirms that email was queued, not delivered to the recipient.

Groups can be listed, created, updated and deleted. Members must belong to the
current organization. Deleting a group removes its supervision assignments
without changing the supervisor's system role.

Employees can change only their own work status. Changes require the status,
expected version and operation identifier. Reading another employee's status or
history retains the existing visibility and supervised-group restrictions.

## Knowledge and files

Actions cover search, details, creation, updates, deletion and document import,
reindexing, attachment upload and deletion, categories and material moves.
Bulk actions attach or detach materials and portal articles to an agent and add
knowledge from a category to an agent.

Files are passed by reference within the current organization. Actions use the
ordinary storage, size checks and quota. Scenario access does not grant access
to another organization or an otherwise inaccessible material.

Knowledge changes may call an indexing provider; attachment changes affect file
storage. Ambiguous failures are not automatically retried as safe operations.
A completed step reuses its stored result. Starting a new step with a new key is
a separate action.

## Organization settings

Actions read and update the organization's name, language, timezone and mode;
read, upload and delete its logo; read the audit log; and configure voice messages
and calls. Mode changes use the ordinary conversation queue transitions.
Personal onboarding can be read, completed, dismissed or restarted.

Demo dataset actions return state and account metadata without passwords.
Installation and removal enqueue the existing worker job. A completed step means
the job was accepted; read the state separately to check its eventual outcome.
These operations require the same organization permissions as the ordinary form.

Secret fields and known connection credentials are redacted before audit results
are persisted. The common editor and journal expose the remaining data with
period, category, result, actor and search filters. Logos use scenario file
references; an ambiguous storage failure does not permit an automatic retry.

## Agents

Actions cover agent listing, directory, card reads, creation, changes, deletion,
activation, deactivation, tools, transport binding/unbinding and test chat.
They use the same domain operations and permissions as the agent card. Scenario
grants cannot replace agent or connection management permissions, or expose
an agent belonging to another organization.

Model parameters omit secret fields and known connection credentials before
results are saved. Tool support checks may contact a provider and use the I/O
executor. Test chat uses the existing AI turn pipeline with preview or execution
mode. It is explicitly treated as potentially effectful, without automatic safe
retry. Provider failures return a failed step without internal diagnostics.
Demo job failures likewise return a localized failure message instead of raw
storage diagnostics. Background action results use the initiating employee's
language, falling back to the organization's language.

## Skills

Template examples support strings, numbers, booleans, objects, mixed lists
and null values. Choose the value type in the shared form; multiline text
keeps its line breaks. The journal displays open fields and nested lists
with the existing secret redaction.

Actions cover listing, full configuration reads, creation, updates, deletion
checks, deletion and agent assignment/removal. Writes use the existing request
identity and expected revision checks. Replaying the same request preserves
domain idempotency; stale changes are rejected. Scenario grants do not replace
skill management permissions or extend access to another organization.

The order skill basis, configuration validation and template preview use the
existing compiler and isolated renderer without installing demonstration data
or executing agent actions. When assigning a skill, pass its current revision;
use the returned revision for subsequent changes because assignment increments it.

## Examples

**Invite into a group.** Create a group and pass its identifier into the employee
creation step's group list. Supply email, full name, position and role. If the
account already exists outside this organization, the result reports an
invitation; there is no new member card yet.

**Import knowledge.** Pass documents with a title, content and category path to
the import action. The result distinguishes created, updated, unchanged and
failed documents. Then add the category's knowledge to an agent; both identifiers
must belong to the same organization.

**Check availability.** Read your own work status, pass its version to the change
step, and supply an operation identifier. If the status has changed in the
meantime, the ordinary version check rejects the stale update.

**Check settings.** Read the organization's settings and pass its language,
timezone or mode to a subsequent step. Select an audit period and category;
secret values never become data for later steps.

Organization-management actions require organization scope. Changing parameters
or invoking a nested scenario cannot widen a parent scenario's or grant's scope.
## Portals and articles

`portals.*` covers portal settings and status, widget selection, domains,
categories, articles, revisions, import, publication, archive and files.
Management actions retain the product's `support.view` / `support.operate`
permissions. A native grant does not expand a contact or conversation scope
into organization administration. Every child resource belongs to the selected
portal in the canonical organization.

Publication selects an existing revision and uses normal knowledge indexing.
Archived content leaves the index, and archived portals retain their editing
restrictions. Import retains per-document outcomes and the product audit event.

`portals.public.*` exposes published content only. Feedback uses the product
rate limit, charged to the organization and the actual initiating membership.
Public file UUIDs retain their product semantics; native downloads additionally
check the organization and return ordinary execution-owned file references.

DNS-dependent settings reads, domain verification, indexed publication and
storage effects use the I/O execution contract. Mutations do not automatically
retry an unknown outcome.

Example: `portals.post` → `portals.categories.post` → `portals.articles.post` →
`portals.article.revision.post` → `portals.article.publish.post`. Bind identifiers
from previous results and use the scenario's confirmation policy. Publish the
portal itself separately with `portals.status.post`.

## Service connections and knowledge files

`services.*` covers adapter discovery, connection lists and details, creation,
rename, pause/resume, deletion, access checks and replacement, and lookups.
Reads require `integrations.view`; mutations and lookups retain the product's
`integrations.manage` requirement. Adapter and authentication labels come from
trusted installed descriptors. Access values are write-only inputs; nested
values are masked in the editor and journal. Results expose presence of access,
never its credentials.

Example: `services.get` → `services.detail.patch` with the selected
`connection_id` and `isActive=false`. `services.check.post` records the normal
connection status and audit; an access failure fails the action without
returning provider diagnostics as ordinary output. Creation and access
replacement perform the product network check. These effects, explicit checks
and deletion of associated files do not automatically retry unknown outcomes.
OAuth retains its interactive redirect, one-time state and callback protocol;
tokens are not action results.

`knowledge.file.get` accepts the public knowledge attachment UUID, verifies its
organization and returns an execution-owned file reference. For example, bind
the result to `portals.article.files.post`: the common file mechanism transfers
bytes while each step enforces its own access rules and storage quota.

## Transport and AI connections

`connections.*` covers connection lists, transport/AI creation, update and
deletion, access checks, MCP tool refresh, and read-only confirmation/revocation.
Service adapters use `services.post` separately. The wrappers share product
commands, proxy normalization, address checks, processing routes and audit.
Every mutation requires `integrations.manage`.

Access keys and header values are secret inputs. An empty key preserves the
stored key; the mask for the same proxy restores its existing password through
the product normalizer. Diagnostics, URLs and credential headers are sanitized
before durable results. A tool confirmation requires `confirmed=true`, records
the acting employee and does not replace step confirmation policy. Unknown
network or file outcomes do not automatically retry.

Example: `connections.post` with WEB, a processing agent and allowed sites →
`connections.assets.post` with a file → `connections.detail.patch` binding the
returned image URL into appearance settings. The widget service enforces SVG
sanitization, formats, size, quotas and organization ownership.
`connections.asset.get` returns the UUID-addressed image as an execution file
after checking the current organization. Public HTTP delivery keeps its original
security headers and immutable address.

The [scenario action guide](native-scenario-actions.en.md) covers management of the scenario mechanism itself.
