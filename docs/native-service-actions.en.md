# Communication and service actions

Choose Chatballs actions from the ordinary scenario step list and combine them
with connected service operations. Supply constants, parameters, conversation
context or a previous step's result. The common launch and journal forms show
their inputs and outcomes.

Each action retains the corresponding application's access rules. A step grant
does not authorize another conversation, another employee's personal template
library or work outside a supervisor's managed groups. Access is checked again
before the next effect. Internal comments remain internal.

## Connected action groups

- Conversations: search, open, counters, employee directory, activity history,
  participation journal, visitor state, claim, return, close, spam, assignment,
  group, priority, note, labels and archiving.
- Contacts: search, card, changes, merge and unmerge. Only the organization owner
  can merge contacts.
- Labels, participants, transfers, reasons and assignment policies.
- Reply templates: personal and shared libraries, categories, labels, variables,
  rendered content and management permissions.
- Handling rules, queue deadlines, rule history and personal notifications.
- Overview statistics, available filters and support reports.
- Quality analysis: settings, history, launch, reports, evidence and reviews.
- Customer ratings: settings, results, conversation cards and responses using
  an existing customer access credential.
- Calls: invite, active call, details, staff cancellation, state and customer
  responses using an existing call access credential.
- Reply assistance: request, attempt history, suggestion details and rejection.
- Mail continuation: saved addresses, available mailboxes, operation history,
  queuing a reply and explicitly retrying an attempt.
- Files: message attachments and audio, contact avatars, conversation diagnostics,
  and CSV/XLSX support report exports.

Messages, internal comments, attachments, voice messages and email replies
use the same delivery services, assignment checks and queues as staff actions.

## AI access

Choose a Chatballs action or scenario and an execution mode in the agent's
existing permissions card. Chatballs actions run on behalf of the administrator
who granted access, using that administrator's current permissions. Approval
by another employee retains that administrator as the source operation's
author; the audit journal identifies both the agent and the administrator.

An existing scenario grant never acquires this authority automatically. When
Chatballs actions are added, an administrator must explicitly change its mode
or turn the grant off and on. Saving an unchanged mode does not assign a
delegate. Blocking or deactivating the administrator, removing their owner/admin
role, or revoking the grant prevents the next effect and the agent's access to
results. Conversation and source feature restrictions apply to every execution.

## Examples

Read a service operation's result, then add an internal comment to the current
conversation. Bind the comment text to a previous result field. A comment does
not send a customer message. Recovering a completed step never appends it twice.

For a support report, supply period bounds with a time zone. An employee with
an action grant can read only their own report; select that employee in the
employee field. Missing historical coverage remains incomplete data, rather
than becoming zero service duration.

Choose “Start quality analysis” for a closed conversation. The step confirms
that analysis was queued. “Awaiting analysis” does not mean conclusions are
available. Read the analysis with a later action after processing and use its
conclusions in subsequent steps.

Criterion scales support text, integer and decimal values. Populate exactly one
of those fields for each value. Integer `1` and decimal `1.0` retain distinct
types. Reviewing a conclusion requires the current review revision and a reason;
the original conclusion is retained. Evidence follows the current management area.

Submitting a rating requires the access credential already issued to that
customer. An action grant never issues it or replaces the customer's answer.
Another organization's, expired or cancelled request is unavailable. Repeating
the same response returns the existing result; a received score cannot be
changed. Preview and journal hide the credential. Disabling ratings cancels
unanswered requests under the application's existing rules.

Call invitations use the connection's existing settings and the employee's
conversation access. The result describes the invitation; ringing does not
mean a connection has been established. Only the participating employee can
cancel the call. Accepting or declining requires the customer's credential;
a staff credential cannot answer for the customer. Actions never issue new
credentials. A call UUID or credential cannot expand the current scenario's scope.

Choose “Request a reply suggestion” and the current conversation for a new
draft. Leave the attempt empty for the first suggestion. To request an
alternative, bind the attempt from an earlier request's result. A completed
step confirms the request; “Awaiting generation” does not mean text is ready.
Read the attempt with another action after processing. Rejection preserves
the original text and decision author, never sends a customer message and
does not change conversation control. An action grant never replaces the
employee's assignment and current permission to reply in that conversation.

A file action returns a file reference usable by a later step. For example,
export the support report as CSV, then bind its “File” result to a subsequent
action's file parameter. The journal shows its name; file contents are never
copied into run text. Exports keep the report's access restrictions; message
files keep their conversation's visibility. The operational copy follows run
retention, while the original message attachment is retained independently.
An unknown outcome never causes an automatic second copy.


For mail continuation, first read the contact's saved addresses and available
mailboxes. Queue a reply using an address and mailbox from that result. Text
may come from an earlier step; an attachment uses a file reference. A completed
step means that the mail operation was created. Read its attempt history
separately: acceptance by a mail server does not confirm delivery to the
recipient. Retrying an unknown outcome requires explicit acknowledgement
of the risk of sending a second message.

Choose “Transcribe a voice message” and the message number in the current
conversation. An existing transcript is returned without a new provider
request. New transcription uses the organization's configured provider and
is stored in the original message. An unknown outcome never causes an
automatic provider retry.

An action grant and the scenario's scope both limit an operation. Access to
one conversation or contact does not authorize organization settings or
global writes. Another contact, message, analysis identifier or call credential
cannot expand that boundary.

Sending text, files or voice uses the normal reply rules: the employee must
see the conversation and have permission to reply; a first reply can claim it
under the existing rules. Bind an attachment to a file value or an earlier
step's file result. Publication and acceptance for transmission never imply
confirmed customer delivery. Unknown outcomes are not retried automatically.
A contact request is available while the customer's phone is not yet saved.

Declining a call from the widget requires an existing visitor session
credential. It is hidden in the journal and is never issued by the action.
The current conversation and organization are checked before changing the
call; an expired session cannot answer an invitation.

The support report includes customer ratings and quality analysis separately
by scale and criteria version, including employee attribution. Original and
reviewed conclusions remain separate. Response rates use the cohort of sent
rating requests; unavailable data or access never becomes a zero result.
Narrowing a saved scenario's scope also limits its previously launched steps.
