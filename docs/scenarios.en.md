# Scenario editor

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
settings. Execution, event subscriptions, launch endpoint, durable waits, AI
grants and actual exchange are supplied by dependent tasks. Saving or enabling a
definition here does not demonstrate a successful external execution.
