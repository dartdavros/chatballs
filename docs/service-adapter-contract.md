# Service adapter contract

## Persistent events and long results

An ingress handler receives the original body bytes, headers and server-built
OperationContext. It verifies the service signature/secret before returning
adapters.events.VerifiedEvent. Never infer tenant/connection from the body.
The server uses the stored connection directory, validates the payload schema,
event identity, timestamp, size and adapter version, then commits encrypted
EventReceipt and an identity-only outbox job before acknowledging the request.

EventDescriptor.replay_seconds declares the finite verified replay horizon.
Missing/invalid horizons are unsupported for ingress; 7/30 history retention
does not invent a delivery protocol. VerifiedEvent contains event_id, event_key,
occurred_at, payload, correlation, optional sequence and optional OperationResult.
The same event identity and normalized digest returns the existing receipt.
A conflicting digest is rejected. Callback before wait registration is matched
again when registering; duplicate/out-of-order jobs never roll back a terminal
checkpoint. A receipt from another organization/connection cannot satisfy a wait.
The app endpoint is POST /api/v1/service-events/<connection-id>/<event-key>/.

OperationResult can supply correlation, event_key and an aware absolute deadline
for a pending callback result. The operation's durable effect_key is available
in OperationContext and can be used as correlation. Resume/reconcile keeps the
same effect key and never re-executes an unsafe write just because its deadline
expired. A terminal callback result must satisfy the frozen operation output
contract. Poll-based continuation still uses durable future outbox jobs.

The independent execution/contract_testing.py module is registered only by
automatic tests. It exercises descriptor loading, typed inputs/results, multiple
connections, long results and signed events without changing the interpreter
or common screens. It is not installed for product UI, does not start a network
server, and does not verify any real brand service.

T-168 implements connection setup, the installed catalog, schemas and preset
metadata. Scenario copies/editor, execution policy, durable runs and event
delivery belong to the following tasks of SPEC-0037. A callable adapter handler
is not a public permission to execute a business action.

## Installing a trusted package

`CHATBALLS_SERVICE_ADAPTERS` lists Python module paths exporting `ADAPTER`, an
immutable `AdapterDescriptor`. `CHATBALLS_SERVICE_EXTENSIONS` lists trusted
modules exporting `EXTENSIONS`, an iterable of `Extension(kind, key, version,
implementation)`. Extensions load before adapters. This is deployment-time
trusted code, not user-uploaded code or hot installation.

An adapter declares a stable key and positive contract version, presentation
keys, settings/access schemas, operations, results, events, lookups, presets and
explicit unsupported capabilities. Connection versions must match the installed
descriptor; an update never silently reinterprets saved settings. The catalog
contains installed descriptors with `listed=True` only. No provider enum or
service-name condition in common UI is required.

## Schemas and handlers

`TypeSpec` supports objects, arrays, string/integer/number/boolean, enum,
date/datetime, lookup and file references; required and nullable are independent.
Objects may explicitly allow additional vendor fields. Files use
`{"fileId": "<UUID>"}`, not inline binary/base64. Validation precedes I/O.

Every operation supplies `execute`; long operations also supply `resume`,
reconciliation strategy supplies `reconcile`, cancellable operations supply
`cancel`. Webhook/callback declarations supply `ingress`; polling supplies
`poll`. A connection check or lookup must use a declared read/search operation.
Handlers receive the server-created tenant/connection context and return
`OperationResult`: completed, pending, failed or unknown. An effect key is not
proof of external idempotency; declare the actual supported retry strategy.

## Initial values for manual creation

`OperationDescriptor.initial_values` declares `InitialValue(target, source,
transform, arguments)` bindings. Targets are explicit paths in the operation's
input schema; sources are paths in the permitted server context. Registration
checks source/target types, registered versioned transforms, their arguments and
overlapping targets. Only create operations can declare these bindings.

The authorized conversation catalog returns an `initialValues` object separately
from `parameters` (the schema). Unknown/blank values are omitted. This read-only
projection does not execute an operation or modify contacts. It is consumed once
when opening the manual form for an action/conversation; later preview, catalog
and lookup responses never merge defaults over employee edits or cleared fields.
Preview and launch receive the employee's exact parameters. Saved scenario
bindings and parameters are independent of these manual defaults.

Bitrix24 declares NAME, PHONE and EMAIL only for lead/contact creation. PHONE
and EMAIL use `list.of_object@1` with VALUE and VALUE_TYPE=WORK, preserving the
single known value of each in the native Contact model. No surname is inferred
from a full name. User lookup labels join trimmed NAME/SECOND_NAME/LAST_NAME,
then fall back to trimmed EMAIL and finally ID; the lookup value remains ID.

## Versioned extensions

References have the form `key@version`. Supported kinds are auth, transport,
transform and control. Duplicate registrations and unknown references fail
startup. The adapter's `transport` defaults to `https@1`; setup checks and saved
connection calls use its selected implementation. A custom transport must preserve
the installation's DNS, redirect, SSRF, timeout, size and private-network policy.

Built-in access extensions are API key (header/query), Basic, Bearer, OAuth2,
HMAC signature, client certificate, secret URL and none. Each adapter declares
only mechanisms appropriate to its protocol. OAuth client configuration belongs
to the server's `CHATBALLS_SERVICE_OAUTH_CLIENTS`, never to browser metadata.

The HTTP helper describes methods, path/query/header parameters, JSON, form and
multipart bodies and response selection. Vendor protocols may supply trusted
handlers. MCP uses the existing guarded Streamable HTTP client. Existing HTTP/MCP
connections have a bridge using their original settings and encrypted secrets;
it neither copies credentials nor changes read-only confirmations/agent access.

Frontend control components register through `registerFieldControl(ref,
component)` before a form is opened. Exact versions are preserved by the API.
Built-in renderers reuse shared text/password/URL, textarea, number, select,
toggle and date controls. A package using lookup/file/compound or a custom form
control must install a matching component and use an approved design. Backend
schema support alone does not install that component. An absent component
blocks form submission and never becomes a text input. The Bitrix24 package uses
the built-in URL control; operation/preset compound schemas are consumed by the
subsequent scenario editor, not exposed as a technical connection wizard.

## Credentials, network and files

Credentials use the existing encrypted field. A top-level branch containing any
nested secret is stored entirely encrypted. Server auth extensions receive that
branch in credentials; nonsecret settings contain no fragment of it. Diagnostic
redaction includes nested secret values. Credentials, authorization headers and
secret webhook paths must not be placed in UI responses, AI input, logs or outbox.

The default transport pins the checked IP and rechecks redirects. Cross-origin
redirects remove authorization headers; client-certificate cross-origin redirects
are refused before contacting the new origin. A refused initial connection is a
failure. Lost or unusable responses after a write may mean an unknown outcome;
they must not trigger a blind retry. Large/binary responses use `ServiceFile` with
the installation's tenant storage and quota accounting.

OAuth state is single-use, expiring and bound to user, organization, adapter and
the connection being restored (or a server-held new-connection draft). A PKCE
verifier is encrypted. Refresh uses a per-connection claim with expiry and fenced
updates, without holding a transaction across network I/O.

## API and presets

Organization-scoped routes under `/api/v1/organizations/<uuid>/integrations/`:

- `GET service-adapters/`: installed catalog, access/settings and operation/result
  schemas, event payload schemas, lookup declarations and presets.
- `GET/POST services/`, `GET/PATCH/DELETE services/<id>/`: lifecycle. PATCH supports
  name and active state; creation checks access where supported.
- `POST services/<id>/check/`, `POST services/<id>/access/`: read-only check and
  replacement of access. `GET services/<id>/lookups/<key>/` reads a declared lookup.
- `POST services/oauth/start/`, `GET services/oauth/<state-id>/`: OAuth setup/status;
  the callback has its dedicated app route.

Presets include purpose, version, required connections/permissions, parameters,
triggers, conditions and ordered steps with input bindings. T-168 does not create
or enable a scenario, even if every connection is configured. Bitrix24 supplies
`create_lead_from_conversation`; copying/editing it is T-169, running it requires
the subsequent executor and entity-link action.

The first Bitrix24 package uses the existing `crm.lead/contact/deal.*` methods;
these remain documented but vendor development has moved to the universal CRM
methods. The package does not claim universal-entity support or incoming event
subscriptions. See the [vendor lead method documentation](https://apidocs.bitrix24.com/api-reference/crm/leads/crm-lead-add.html)
and [webhook documentation](https://apidocs.bitrix24.com/local-integrations/local-webhooks.html).

## Verification

Run backend tests through the managed environment's `backend-admin` with
`python -m pytest --reuse-db -q chatballs/integrations/adapters
chatballs/integrations/service_connections`. These are isolated automated tests;
the probe adapter is never installed for product/browser demonstrations. Check
the actual installed Bitrix24 package in the task browser with a real authorized
webhook. Connection verification calls `scope` and declared read-only lookups;
it must not create CRM records just to demonstrate setup.
