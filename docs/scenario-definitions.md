# Scenario definition contract, version 1

The editor and preset copies persist one document. Ownership, public ID, enabled
state, origin and optimistic `revision` belong to `ScenarioDefinition`, never to
user input fields. The encrypted document contains `version`, `parameters`,
`results`, `outputs`, `triggers`, `conditions`, `steps`, `access`, `synchronization`.

Schemas use `type`, `required`, `nullable`, nested `properties`/`items`, `options`,
`lookup`, `open` and presentation `title`. Types mirror adapter TypeSpec. The
server derives operation/event/result/context schemas from installed packages,
and tenant references from the active organization. Unknown document fields and
unsupported structure are rejected even for disabled drafts. Semantic omissions
may be saved disabled but cannot be enabled.

## Blocks and bindings

Every trigger/block has a stable unique string ID. `action` selects `connection`,
`target` and typed `inputs`; `if` has `condition`, `then`, `else`; `foreach` has
`list`, `body`, `concurrency` (1–5), `onError`; `parallel` has at least two
`branches` and `onError`; `call` selects scenario public ID and supplies `inputs`;
`try` has `body`, `catch`, `after`; `wait` supports duration, datetime, local clock,
event, reply or employee confirmation, timeout and expiration handling.

A binding is `{source: constant, value: ...}` or a typed reference to
`input`/`parameter` (name), `context`/`event` (path), `step`/`item`/`error`
(step ID and path). Objects/lists can contain mixed bindings. Optional `transform`
selects a registered `key@version`; `args` must satisfy its declared schema.
Constants are literal data, including objects with a property named `source`.
Only an object whose own `source` is a string is interpreted as a binding.

Previous results are lexical: future steps, sibling branch results and iteration
items outside their loop are unavailable. Catch details belong only to the
matching try block. Event data is available only when compatible for every
configured launch method. `values.prepare_inputs` validates resolved values and
tenant file references before a future executor may call a domain effect; it
does not execute handlers or replace principal/permission checks.

Step outcome is a distinct reference `{source: step, step: ..., aspect: state}`,
typed as `completed` / `failed`; it never guesses an outcome from business data.
`RunValues.states` must contain a recorded outcome. Contact presence/absence,
label scope and channel predicates use server-derived tenant catalogs. Linked
record predicates validate the selected connection/entity pair. These are saved
declarations; runtime predicate evaluation belongs to the executor tasks.

`entity_link.create` accepts only a tenant-checked constant connection/entity
selection from the editor, with a typed external record ID. Arbitrary adapter
business dictionaries are never scanned as identity or connection references.

## Editing API

Routes below are relative to `/api/v1/organizations/<uuid>/integrations/`.
All editor routes require `integrations.manage` (OWNER/ADMIN).

- `scenarios/`: list or create. POST accepts name, definition, enabled.
- `scenarios/<uuid>/`: read, PUT with current revision, DELETE with revision.
- `scenarios/check/`: pure definition validation, with issue paths/codes/text.
- `scenarios/catalog/`: server-derived editor schemas and tenant references.
- `scenarios/<uuid>/copy/`: independent disabled copy, revision 1.
- `services/<id>/presets/<key>/`: independent disabled preset copy.
- `scenarios/<uuid>/keys/<trigger>/rotate/`: explicit key rotation with revision.
- `services/<id>/synchronization/`: read/PUT versioned exchange configuration
  with optimistic revision; uses the same synchronization validator/document
  structure as scenario definitions.

Stale updates/deletes return 409. Foreign resources are hidden. Scenario connection
references have tenant-checked FKs. New tables use existing runtime RLS/role
grants, without extra services. Definitions/exchange values are encrypted; external
keys are stored as hashes, returned only upon creation/rotation. Audit stores
identifiers and revision, never definition contents or keys.

## Presets and exchange

An adapter can supply `ScenarioTemplate.definition`, the full versioned document,
with `connection: self` placeholders in structural connection fields. `labels`
maps presentation paths to translation keys. Legacy T-168 action templates are
normalized once when copied, never interpreted as a second runtime DSL. Copies
record adapter/key/version; package updates never write existing copies.
Presentation paths address only step names or schema titles. Nested condition,
wait, trigger and synchronization connection placeholders are replaced; constant
business values named `connection` remain literal data.

Entity descriptors supply fields and eligible native entity pairs. A synchronization
pair stores two connection/entity endpoints, enabled state, direction, independent
field mappings, source of truth, conflict/deletion policy and mandatory causality
guards. Mapping `values` is directed; null destination preserves the receiving
value. Reverse tables are never inferred. Identity fields cannot be writable
destinations. No matching/linking or synchronization is performed while editing.

Execution and publication remain with T-170–T-176. In particular, external key
metadata describes the agreed future launch endpoint; this task does not install
its handler, manufacture run records or claim that configured waits/schedules run.
