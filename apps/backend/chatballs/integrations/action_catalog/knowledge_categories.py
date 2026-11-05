"""Knowledge category actions preserve the existing hierarchy and content policy."""

from chatballs.ai import category_management as service
from chatballs.integrations.action_catalog.schema import action, obj, required
from chatballs.integrations.adapters.contracts import Effect, OperationResult, ResultState
from chatballs.integrations.adapters.schema import TypeSpec

NAME = TypeSpec("string", title_key="native.knowledge_categories.name")
PARENT = TypeSpec("integer", nullable=True, title_key="native.knowledge_categories.parent")
ORDER = TypeSpec("integer", title_key="native.knowledge_categories.order")
IDENTIFIER = TypeSpec("integer", required=True, title_key="native.knowledge_categories.identifier")
CATEGORY = obj(id=TypeSpec("integer"), name=NAME, parentId=PARENT, sortOrder=ORDER,
    isSystem=TypeSpec("boolean", title_key="native.knowledge_categories.system"),
    knowledgeCount=TypeSpec("integer", nullable=True, title_key="native.knowledge_categories.count"))
OUTPUT = TypeSpec("object", properties=(("category", TypeSpec("object", properties=CATEGORY.properties,
    title_key="native.knowledge_categories.category")),))


def listing(context, values):
    return OperationResult(ResultState.COMPLETED, service.list_categories(context.tenant))


def create(context, values):
    return OperationResult(ResultState.COMPLETED, service.create_category(context.tenant, values))


def update(context, values):
    return OperationResult(ResultState.COMPLETED,
        service.update_category(context.tenant, values["category_id"], values))


def delete(context, values):
    service.delete_category(context.tenant, values["category_id"])
    return OperationResult(ResultState.COMPLETED, {})


for key, inputs, outputs, handler, method, capability, suffix, view, effect in (
    ("knowledge.categories.get", obj(), obj(items=TypeSpec("array", items=CATEGORY)), listing, "GET",
        "ai.view", "", "KnowledgeCategoryListCreateView", Effect.READ),
    ("knowledge.categories.post", obj(name=required(NAME), parentId=PARENT, sortOrder=ORDER), OUTPUT,
        create, "POST", "ai.manage", "", "KnowledgeCategoryListCreateView", Effect.CREATE),
    ("knowledge.category.patch", obj(category_id=IDENTIFIER, name=NAME, parentId=PARENT, sortOrder=ORDER),
        OUTPUT, update, "PATCH", "ai.manage", "<int:category_id>/", "KnowledgeCategoryDetailView", Effect.UPDATE),
    ("knowledge.category.delete", obj(category_id=IDENTIFIER), obj(), delete, "DELETE", "ai.manage",
        "<int:category_id>/", "KnowledgeCategoryDetailView", Effect.DELETE),
):
    action(key=key, title=f"native.{key}", input=inputs, output=outputs, handler=handler,
        capability=capability, scope="organization", route=f"ai/knowledge/categories/{suffix}",
        view=f"chatballs.ai.category_views.{view}", method=method, effect=effect)
