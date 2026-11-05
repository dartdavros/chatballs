# Scenario editor

AI permissions and confirmations: [agent actions](agent-actions.en.md).

Application operations and examples: [communication and service actions](native-service-actions.en.md).

## Composite steps and waits

A sequence advances after recording the previous outcome. A condition selects
one branch using actual values; a missing required value stops the action rather
than becoming false. A loop snapshots its list once and records each iteration.
Continuing after an item error preserves the other results. Parallel branches
keep independent checkpoints and join their outcomes. Recovery never repeats
already completed effects.

Error handling receives a safe reason, the failed step name and number, service
and run. It can continue or finish with failure after the handler. An unknown
write outcome requires reconciliation and never becomes an ordinary catch error.
Compensation is a separate explicitly permitted action.

A nested call supplies required inputs and returns a validated result. The
callee must enable nested invocation and delegation. It has its own Run and
intersects the caller's permissions with its own. Cycles are rejected. Definition
edits do not change an active snapshot; disabling or revoking access stops new
effects.

A wait releases the worker. Duration, fixed date/time, local clock, customer
reply, service event and assigned employee decision keep persistent deadlines.
A matching early event after Run creation is retained; another connection cannot
resume the wait. A decision binds exact data and expiry and cannot resume twice.
A working day needs a working calendar; choose a fixed date or duration when one
is unavailable. A long service result has its own deadline. Expiry does not prove
that the service did nothing.

Run details retain block, branch and iteration states, confirmation parameters
and recorded results. Viewing does not grant continuation authority. Technical
depth, iteration, volume and time limits are explained without hiding partial
outcomes.

Example custom scenario: read the first service → test a result field → process
documents → run independent actions in two connections → wait for confirmation
→ invoke a permitted nested scenario with the first result. Ordinary blocks
compose this scenario without a core change. Available operations and fields
come from installed adapters. This example does not claim a verified external
service connection.

Organization owners and administrators can open Settings → Scenarios, create a
scenario, or configure a preset from a service connection. A preset becomes an
editable organization copy. Adapter updates do not overwrite that copy.

## Launch → Conditions → Steps

Choose employee, AI, Chatballs event, service event, schedule, external API or
another scenario as launch methods. Configure employees/groups, context, AI mode,
confirmation and delegation. Saving does not execute an action or grant rights.

Schedules use the organization's timezone, frequency, days/time and missed-launch
policy. The stored daylight-saving policy uses the first occurrence of repeated
local time and skips nonexistent local time.

Select connections, operations and fields supplied by installed adapters. Values
can be constants, employee/AI input, allowed context, event data, a previous
step's field, an iteration item or error details. Nested objects/lists use the
same forms. Registered typed transforms and organization file references are
supported. Arbitrary program code is never executed.

Use If, For each, In parallel, Run another scenario, Wait and On error to compose
the workflow. Each branch, loop and error handler has its own step list. Error
details include reason, step, service and run. The caller supplies a nested
scenario's required inputs; nested execution must not increase permissions.

## Saving and conflicts

Save incomplete definitions disabled. Enabling validates required values, types
and references. Actual values must be validated again before an effect. A stale
revision cannot overwrite another administrator's changes. Load the latest
version and reapply your edits. Leaving an unsaved draft offers save, discard
or cancel.

An API launch method issues its address and example request after saving. Copy
the new key before closing its panel: it is only shown once. Later reads show a
mask. Explicit rotation replaces the stored key hash and removes the old value.

## Exchange

Open Data exchange in the service card. Select linked record pairs, directions,
fields and independent value mappings for each direction. Leave unchanged
preserves the receiving value. Configure conflict and deletion handling. Matching
phone/email values never create a link automatically.

## Configuration examples

To check the structure without an external service, create a scenario launched
by an employee. Add Conversation contact → Contact is present as a condition,
then Wait → a duration of one hour. Save and reopen it: both settings should
remain. This checks the definition, not its execution.

To process a list, select an installed service operation that returns a list.
Add For each and choose the first step's list. Add an action inside the loop;
its fields can use Current item. Add Try / on error to configure separate main
and error lists; the handler can use Error details. After a step, Result of step
→ Step outcome lets a condition select completion or failure. Future results
and sibling branch results are unavailable.

## Delivery scope

This delivery saves and validates definitions, external launch keys and exchange
settings. Manual single-step service actions use the shared executor. Event
subscriptions, the external launch endpoint, composed workflows, durable waits,
AI grants and actual exchange are supplied by dependent tasks. Saving or enabling a
definition here does not demonstrate a successful external execution.

## Manual execution and results

In an accessible conversation, open Actions or an action on the contact card.
Fill in its parameters and review what will happen before selecting Run.
The command creates one run with immutable parameters. If the response is lost,
retrying in the same form returns that run. Editing the scenario does not change
an existing run. If the action version changes, review the connection and scenario;
confirmation of old parameters cannot authorize new ones.

The timeline card opens the actual outcome and step details. Conversation
visibility permits reading its runs, but does not grant action permissions or
access to the organization journal. Owners and administrators can search and
filter Settings → Scenarios → Run journal by service, initiator, period and state.
Refreshing the journal never sends the action again.

## Lost responses, reconciliation and cancellation

Outcome unknown means the service may have completed the request without a
confirmed response. It is neither success nor proof that no record was created.
Select Check outcome first. When supported, the executor reconciles the original
effect. Without a safe reconciliation or retry strategy, the outcome stays unknown.
Check the external service before creating another run after a network failure.

Run again is a separate intentional command recorded in the audit. It can create
a duplicate. Establish the original outcome first. A new run requires current
permissions and confirmation of its exact parameters. Opening a different form
creates a new command rather than continuing the previous one.

Cancel run stops new actions. A request already sent can still finish, and its
actual result remains recorded. Cancellation does not delete external records or
undo confirmed success. Compensation is a separate authorized service action.

## Retention

Owners and administrators configure retention in Settings → Organization.
Defaults are 7 days for step details and 30 days for history, measured from run
completion. Active runs and waits are protected. Operational files are removed
once no protected run or independent owner needs them. Details cannot outlive history.

A shorter period requires explicit confirmation and takes effect no earlier than
24 hours later. Restore the old period before deletion to cancel the reduction.
Longer periods cannot restore deleted data. Cleared details cannot be recovered
from the safe journal. After history expires, only minimal command deduplication
identity remains. The audit retains its own policy.

## Automatic launches

In Launch, choose a Chatballs event, a connected service event, a schedule, or
the external API. Enable Allow launching without an employee after reviewing
the steps: the scenario uses your administrator permissions, checked before
every action. Copies do not inherit this authorization automatically. Disabling
a scenario stops new actions.

One event can launch several independent scenarios. Redelivery and definition
edits do not repeat the same scenario event. One subscriber failing does not
cancel the others. Pausing a connection preserves accepted delivery for resume;
a disabled scenario does not replay events received while it was disabled.
The scenario editor/list shows a stopped launch reason; the journal shows
results for executions that have started.

Schedules retain the organization's time zone. Choose a time, weekdays or a day
of the month, and a missed-launch policy. Run once catches up only the latest
missed slot; Skip does not catch up. Normal servicing delays of up to a minute
still belong to the current slot. By default a missing daylight-saving time is
skipped and a repeated local time uses its first occurrence once. Editing a
scenario does not repeat an already processed slot.

Save an API scenario and copy its generated address, new key and request example.
The key is shown once; rotation revokes the old key. Each new command needs its
own Idempotency-Key header; retries of that command reuse the same value. Inputs
are sent in parameters. The response identifies the run and its actual state,
without promising a completed effect. The key cannot authorize another scenario
or an inaccessible conversation.

## Linked records and data exchange

Linked records in a conversation show records explicitly linked by scenarios.
Link another record searches first: select the intended result and confirm.
The first candidate is never selected automatically. If none is found, try
another number or name. Unlinking/replacing does not change or delete the remote
record. A matching email or phone does not prove identity or merge contacts.

Data exchange in a service card processes existing links only. Enable the
required entity pairs and choose directions, field mappings, source of truth,
conflict policy and deletion behavior. Conversation status and service stage
maps are independent in each direction. Unmapped values preserve the receiving
status. An unsupported adapter direction cannot be enabled; an unconditional
write does not substitute for a current-version check.

With Do not change, the journal's Needs attention group shows Decision needed.
An owner or administrator selects a value for every field and chooses Apply
in both systems. Saving the selection has not completed the writes: wait for
the step results. If either record has changed, the stale decision is rejected.
Refresh the values and review the change again.

A running execution keeps its original link; later executions use the new one.
Deletion follows the selected policy and supported domain action. An access
failure is not evidence of deletion. Exchange does not reopen closed
conversations. Partial success and unknown outcomes remain visible in the
journal; inspect them before intentionally launching again.
