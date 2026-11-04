# Agent actions

The agent card’s Actions and scenarios section lists operations of connected
services and enabled scenarios whose launch settings select this agent.
An owner or administrator chooses a mode for each target and saves changes:

- Forbidden: the agent is not offered the action.
- Independently: the agent may execute without an employee, including explicitly
  permitted creation, updates and deletion.
- With confirmation: an employee first reviews the exact values and context.

The scenario editor and agent card edit the same permission. Existing tools
and skills do not enable new actions automatically. Disabled connections and
scenarios are unavailable; restoring a connection does not restore a revoked grant.

## Confirmation in a conversation

Employees see the request in the feed. Review the action, connection and every
parameter, including the external assignee. An administrator or the currently
authorized conversation assignee decides. Being able to see a request as a
participant does not grant permission to confirm it.

The request is valid for 30 minutes and applies to those exact values. Edit opens
the current request’s fields without changing the scenario definition. Another
employee cannot confirm while it is being edited. Confirm with changes approves
the new values; an earlier confirmation cannot authorize them. Reject stops new
effects and does not undo an established result. Customer, model and event text
never counts as employee consent.

## Testing an agent

Configuration check is selected by default: inputs are validated without creating
a run or changing the service. The card says Not executed. Explicitly select
Real execution to launch actions. Its warning explains that changes in external
services are real. The same permissions and action mode apply; testing never
bypasses an employee’s required confirmation.

## Results

The agent receives the run identifier and actual state. Waiting and running do
not mean success. The card updates as execution progresses. Details open from
the conversation and remain inside the chat on a phone. The model may request
current status in a subsequent turn. Completion does not create a second,
unbounded conversation loop or switch providers.

Current permissions and conversation control are checked before a new effect
and reply. After takeover, disabling AI or revoking access, an older run cannot
authorize a late autonomous reply, even if control is later returned. An already
sent request may finish; its actual outcome is retained in the journal.

See [scenario help](scenarios.en.md) for retention and recovery.
