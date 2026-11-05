"""Group and assignee operations retain domain policy, version and event guards."""

from rest_framework.exceptions import ValidationError

from chatballs.conversations.assignment import assign_operator, move_conversation
from chatballs.conversations.transfer_transition import transfer_input, transfer_payload
from chatballs.i18n import t
from chatballs.identity.group_models import EmployeeGroup
from chatballs.identity.models import OrganizationMembership
from chatballs.integrations.action_catalog.resources import (
    CONVERSATION,
    CONVERSATION_RESULT,
    audit,
    conversation,
    conversation_result,
)
from chatballs.integrations.action_catalog.schema import (
    CONVERSATION_ID,
    TEXT,
    action,
    obj,
    required,
)
from chatballs.integrations.action_catalog.transfer_schemas import TRANSFER
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def group(context, values):
    current = conversation(context.tenant, values["conversation_id"], "conversations.transfer")
    target = None
    if values.get("group_id") is not None:
        target = EmployeeGroup.objects.filter(organization_id=context.tenant.organization_id,
            pk=values["group_id"]).first()
        if target is None:
            raise ValidationError(t("admin.group_not_found"))
    row = move_conversation(context=context.tenant, conversation_id=current.pk, group=target)
    audit(context.tenant, "group_changed", row)
    return OperationResult(ResultState.COMPLETED, conversation_result(context.tenant, row))


def assignee(context, values):
    current = conversation(context.tenant, values["conversation_id"], "conversations.assign")
    fields = {key: values[key] for key in ("userId", "expectedVersion", "reasonId", "comment") if key in values}
    if set(fields) != {"userId"}:
        data = transfer_input({**fields, "operationId": context.effect_key})
        row = assign_operator(context=context.tenant, conversation_id=current.pk, transfer=data)
        return OperationResult(ResultState.COMPLETED, {"transfer": transfer_payload(row)})
    target = None
    if fields["userId"] is not None:
        member = OrganizationMembership.objects.select_related("user").filter(
            organization_id=context.tenant.organization_id, user_id=fields["userId"],
            blocked_at__isnull=True, user__is_active=True).first()
        if member is None:
            raise ValidationError(t("admin.employee_not_found"))
        target = member.user
    row = assign_operator(context=context.tenant, conversation_id=current.pk,
        assignee=target, operation_id=context.effect_key)
    audit(context.tenant, "assignee_changed", row)
    return OperationResult(ResultState.COMPLETED, conversation_result(context.tenant, row))


action(key="conversations.group.post", title="native.conversation_group",
    input=obj(conversation_id=CONVERSATION_ID, group_id=TypeSpec("integer", nullable=True)),
    output=CONVERSATION_RESULT, handler=group, capability="conversations.transfer", scope="conversation",
    route="conversations/<int:conversation_id>/group/", view="chatballs.conversations.management_views.ConversationGroupView", method="POST")

action(key="conversations.assignee.post", title="native.conversation_assignee",
    input=obj(conversation_id=CONVERSATION_ID, userId=required(TypeSpec("integer", nullable=True)),
        expectedVersion=TypeSpec("integer"), reasonId=TypeSpec("integer"), comment=TEXT),
    output=obj(conversation=CONVERSATION, transfer=TRANSFER), handler=assignee,
    capability="conversations.assign", scope="conversation", route="conversations/<int:conversation_id>/assignee/",
    view="chatballs.conversations.management_views.ConversationAssigneeView", method="POST")
