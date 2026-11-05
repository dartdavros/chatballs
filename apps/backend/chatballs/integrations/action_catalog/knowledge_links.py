"""Mass operations preserve the source content service's tenant checks."""

from functools import partial

from chatballs.ai import content_link_commands as commands
from chatballs.integrations.action_catalog.knowledge_schemas import field
from chatballs.integrations.action_catalog.schema import action, obj
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

IDS = TypeSpec("array", items=TypeSpec("integer"), required=True)
ACTION = field("action", "enum", options=tuple(EnumOption(value, f"native.knowledge_link.{value}")
    for value in ("attach", "detach")))
AGENT = field("agent", "integer", required=True)
CATEGORY = field("category", "integer", required=True)


def selected(name):
    from dataclasses import replace
    return replace(IDS, title_key=f"native.knowledge_fields.{name}")


def link_result(name):
    return obj(agentId=AGENT, action=ACTION, changed=field("changed", "integer"),
        changedIds=selected("changedIds"), skippedIds=selected("skippedIds"), **{name: selected(name)})


def execute(context, values, *, command, category=False):
    args = (context.tenant, values["agent_id"], values) if category else (context.tenant, values)
    return OperationResult(ResultState.COMPLETED, command(*args))


for key, inputs, outputs, command, category, route, view in (
    ("knowledge.bulk.move", obj(knowledgeIds=selected("knowledgeIds"), categoryId=CATEGORY),
        obj(updated=field("updated", "integer"), knowledgeIds=selected("knowledgeIds")),
        commands.move, False, "knowledge/bulk/move/", "KnowledgeBulkMoveView"),
    ("knowledge.bulk.agent", obj(knowledgeIds=selected("knowledgeIds"), agentId=AGENT, action=ACTION),
        link_result("knowledgeIds"), commands.link, False, "knowledge/bulk/agent/", "AgentKnowledgeLinkView"),
    ("knowledge.portal_articles.agent", obj(articleIds=selected("articleIds"), agentId=AGENT, action=ACTION),
        link_result("articleIds"), partial(commands.link, articles=True), False,
        "portal-articles/bulk/agent/", "AgentPortalArticleLinkView"),
    ("knowledge.agent.select_category", obj(agent_id=AGENT, categoryId=CATEGORY),
        obj(agentId=AGENT, categoryId=CATEGORY, addedKnowledgeIds=selected("addedKnowledgeIds"), knowledgeIds=selected("knowledgeIds")),
        commands.select_category, True, "agents/<int:agent_id>/knowledge/select-category/", "AgentCategoryKnowledgeSelectView"),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs,
        handler=partial(execute, command=command, category=category),
        capability="ai.manage", scope="organization", route=f"ai/{route}",
        view=f"chatballs.ai.bulk_views.{view}", method="POST", effect=Effect.UPDATE)
