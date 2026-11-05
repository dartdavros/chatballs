"""Rule actions reuse settings/scheduler; they do not install another event path."""

from dataclasses import replace

from chatballs.conversations.queue_policy_service import queue_policy
from chatballs.conversations.rules.operations import change_rule, list_rules, rule_journal
from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.rule_schemas import (
    EXECUTION,
    KIND,
    QUEUE,
    QUEUE_FIELDS,
    RULE,
    RULE_CHANGES,
    STATUS,
)
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec


def listing(context, values):
    return OperationResult(ResultState.COMPLETED, list_rules(context.tenant))


def update(context, values):
    return OperationResult(ResultState.COMPLETED, change_rule(context.tenant, values["kind"],
        {key: value for key, value in values.items() if key != "kind"}))


def journal(context, values):
    return OperationResult(ResultState.COMPLETED, rule_journal(context.tenant, values))


def queue(context, values):
    return OperationResult(ResultState.COMPLETED, queue_policy(context.tenant))


def update_queue(context, values):
    return OperationResult(ResultState.COMPLETED, queue_policy(context.tenant, values))


for key, title, inputs, output, handler, method, route, view, module, capability in (
    ("rules.get", "native.rules_list", obj(), obj(items=TypeSpec("array", items=RULE)),
        listing, "GET", "rules/", "RuleListView", "rules.views", "settings.view"),
    ("rules.rule.patch", "native.rules_update", obj(kind=required(KIND), **RULE_CHANGES), obj(rule=RULE),
        update, "PATCH", "rules/<str:kind>/", "RuleDetailView", "rules.views", "settings.manage"),
    ("rules.journal.get", "native.rules_journal", obj(kind=KIND, status=STATUS,
        conversationId=TypeSpec("integer"), **PAGE_INPUTS), replace(page_of(EXECUTION),
            properties=page_of(EXECUTION).properties + obj(timezone=TypeSpec("string")).properties),
        journal, "GET", "rule-executions/", "RuleExecutionListView", "rules.views", ""),
    ("conversations.queue_policy.get", "native.queue_policy", obj(), QUEUE,
        queue, "GET", "queue-policy/", "QueuePolicyView", "queue_policy_views", "settings.view"),
    ("conversations.queue_policy.patch", "native.queue_policy_update", obj(**QUEUE_FIELDS), QUEUE,
        update_queue, "PATCH", "queue-policy/", "QueuePolicyView", "queue_policy_views", "settings.manage"),
):
    action(key=key, title=title, input=inputs, output=output, handler=handler, method=method,
        route=f"conversations/{route}", view=f"chatballs.conversations.{module}.{view}",
        capability=capability, scope="organization")
