"""A native I/O action of the shared runner, never another AI worker or LLM cycle."""

from django.conf import settings
from django.utils import timezone

from chatballs.ai.execution_policy import execution_guard
from chatballs.ai.provider.base import ProviderError
from chatballs.ai.turn import record_turn, run_turn_chat, turn_pseudonymizer
from chatballs.conversations.ai_turn_result import store_answer
from chatballs.conversations.ai_turn_state import Turn
from chatballs.integrations.action_catalog.contracts import NativeOperationRejected
from chatballs.integrations.action_catalog.registry import native_action
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.execution.native_results import save as save_receipt
from chatballs.integrations.execution.permissions import ExecutionDenied, authorize_run
from chatballs.integrations.scenario_state.runs import ScenarioRun
from chatballs.integrations.scenario_state.steps import ScenarioStep
from chatballs.tenancy.database import tenant_atomic
from chatballs.webchat.proactive_guards import current, for_run
from chatballs.webchat.proactive_models import SiteEventLaunch
from chatballs.webchat.proactive_plan import first_plan, instruction


def completed(state, message_id=None):
    return OperationResult(ResultState.COMPLETED, {"state": state, "messageId": str(message_id) if message_id else None})


def execute(context, values):
    tenant = context.tenant
    claim = None
    try:
        with tenant_atomic(tenant):
            run = ScenarioRun.objects.get(public_id=context.run_id, organization_id=tenant.organization_id)
            step = ScenarioStep.objects.get(run=run, path=context.step_path, effect_key=context.effect_key)
            claim = for_run(run)
            if claim is None:
                raise NativeOperationRejected("permission")
            claim, session, conversation = current(tenant, claim, allow_sent=True)
            authorize_run(tenant, run)
            if claim.response_id:
                return completed("sent", claim.response_id)
            if claim.state != "pending" or conversation is None:
                return completed("suppressed")
            query = instruction(run, step)
            claim.state = "running"
            claim.save(update_fields=["state"])
            turn = Turn(message=None, conversation=conversation, agent=conversation.channel.ai_agent,
                user_id=session.identity.external_user_id, query=query, history=[],
                pseudonymizer=turn_pseudonymizer(conversation), is_new_conversation=True,
                mode_version=claim.mode_version, control_version=claim.control_version, site_event_launch_id=claim.pk)
            fence = step.fence
    except ExecutionDenied:
        if claim is not None:
            with tenant_atomic(tenant):
                SiteEventLaunch.objects.filter(pk=claim.pk, state__in=("pending", "running")).update(state="suppressed")
        return completed("suppressed")

    def permitted():
        try:
            with tenant_atomic(tenant):
                current(tenant, claim)
                fresh_run = ScenarioRun.objects.get(pk=run.pk, organization_id=tenant.organization_id)
                actual_step = ScenarioStep.objects.get(pk=step.pk, run=fresh_run)
                if (actual_step.fence != fence or actual_step.state != "running"
                        or not actual_step.lease_until or actual_step.lease_until <= timezone.now()):
                    return False
                authorize_run(tenant, fresh_run)
                return True
        except ExecutionDenied:
            return False

    try:
        with tenant_atomic(tenant):
            if not permitted():
                raise ExecutionDenied("site_event_suppressed")
            plan = first_plan(turn, run, claim)
        with execution_guard(permitted):
            answer = run_turn_chat(plan, time_left=min(settings.CHATBALLS_AI_TURN_DEADLINE_SECONDS,
                max(0, (step.lease_until - timezone.now()).total_seconds())))
        with tenant_atomic(tenant):
            text = record_turn(agent=turn.agent, plan=plan, answer=answer)
            if not permitted():
                raise ExecutionDenied("site_event_suppressed")
            run.refresh_from_db()
            step.refresh_from_db()
            claim, session, turn.conversation = current(tenant, claim)
            authorize_run(tenant, run)
            if answer.error is not None or not text.strip():
                raise NativeOperationRejected("site_event_failed")
            run_ids = [c.action_result["runId"] for c in answer.tool_calls if c.action_result.get("runId")]
            if run_ids:
                from chatballs.integrations.execution.ai_reply import allowed
                if not allowed(tenant, turn.conversation.pk, run_ids):
                    raise ExecutionDenied("site_event_suppressed")
            store_answer(turn=turn, context=tenant, text=text, prepared=answer.prepared_reply)
            message = turn.conversation.messages.get(ai_delivery__siteEventLaunchId=claim.pk)
            claim.response = message
            claim.state = "sent"
            claim.save(update_fields=["response", "state"])
            result = completed("sent", message.pk)
            # The message, once marker and normal native receipt are one commit.
            save_receipt(run, step, native_action("webchat.first_reply"), result, actor=tenant)
            return result
    except (ExecutionDenied, ProviderError, NativeOperationRejected) as error:
        with tenant_atomic(tenant):
            suppressed = not permitted()
            SiteEventLaunch.objects.filter(pk=claim.pk, response__isnull=True).update(
                state="suppressed" if suppressed else "failed")
        if suppressed:
            return completed("suppressed")
        raise NativeOperationRejected("site_event_failed") from error
