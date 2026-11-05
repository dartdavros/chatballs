"""Reply library schemas keep ownership and relation fields explicit."""

from chatballs.integrations.action_catalog.schema import TEXT, obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec

SCOPE = TypeSpec("enum", options=(EnumOption("SHARED", "native.templates_shared"),
    EnumOption("PERSONAL", "native.templates_personal")))
TITLE = TypeSpec("string", max_length=120)
IDS = TypeSpec("array", items=TypeSpec("integer"))
TAXONOMY = obj(id=TypeSpec("integer"), name=TITLE, scope=SCOPE, ownerId=TypeSpec("integer", nullable=True))
TEMPLATE = obj(id=TypeSpec("integer"), title=TITLE, text=TEXT, updatedAt=TypeSpec("datetime"),
    scope=SCOPE, ownerId=TypeSpec("integer", nullable=True), categoryId=TypeSpec("integer", nullable=True), tagIds=IDS)
VARIABLE = obj(key=TEXT, token=TEXT, label=TypeSpec("string", title_key="native.variable_label"), type=TypeSpec("string", title_key="native.variable_type"), connectionId=TypeSpec("integer"), connectionName=TEXT)
