"""Explicit knowledge contracts for the common editor and result renderer."""

from dataclasses import replace

from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec


def field(name, kind="string", **options):
    if kind == "string" and name in {"content", "description"}:
        options.setdefault("control", "textarea@1")
    return TypeSpec(kind, title_key=f"native.knowledge_fields.{name}", **options)


ID = field("knowledge", "integer", required=True)
CATEGORY = obj(id=field("category", "integer"), name=field("categoryName"),
    parentId=field("parent", "integer", nullable=True))
ATTACHMENT = obj(id=field("attachment", "integer"), name=field("name"),
    contentType=field("contentType"), size=field("size", "integer"), hasText=field("hasText", "boolean"),
    url=field("url"), createdAt=field("createdAt", "datetime"))
AGENT = obj(id=field("agent", "integer"), name=field("name"), groupName=field("groupName", nullable=True),
    aiStatus=field("aiStatus", "enum", options=tuple(EnumOption(value, f"native.knowledge_status.{value}")
        for value in ("DRAFT", "ACTIVE", "DISABLED", "ARCHIVED"))))
KNOWLEDGE = obj(id=replace(ID, required=False), title=field("title"), description=field("description"),
    category=replace(CATEGORY, title_key="native.knowledge_fields.category"),
    isEnabled=field("isEnabled", "boolean"), attachments=field("attachments", "array", items=ATTACHMENT),
    agentsCount=field("agentsCount", "integer", nullable=True),
    agentIds=field("agentIds", "array", items=TypeSpec("integer")),
    fragmentsCount=field("fragmentsCount", "integer", nullable=True),
    createdAt=field("createdAt", "datetime"), updatedAt=field("updatedAt", "datetime"),
    updatedBy=field("updatedBy"), createdBy=field("createdBy"), content=field("content"),
    agents=field("agents", "array", items=AGENT))
OUTPUT = obj(knowledge=replace(KNOWLEDGE, title_key="native.knowledge_fields.knowledge"))
FIELDS = {"title": field("title"), "description": field("description"), "content": field("content"),
    "isEnabled": field("isEnabled", "boolean"), "categoryId": field("category", "integer")}
FILTERS = obj(**PAGE_INPUTS, category=field("category", "integer"),
    isEnabled=field("isEnabled", "boolean"), search=field("search"),
    agent=field("agentIds", "array", items=TypeSpec("integer")))
PAGE = page_of(KNOWLEDGE)
DOCUMENT = obj(title=field("title", required=True), content=field("content", required=True),
    description=field("description", nullable=True),
    categoryPath=field("categoryPath", "array", items=TypeSpec("string")))
IMPORT = obj(documents=field("documents", "array", items=DOCUMENT, min_items=1, required=True))
IMPORT_RESULT = obj(created=field("created", "integer"), updated=field("updated", "integer"),
    unchanged=field("unchanged", "integer"), failed=field("failed", "array",
        items=obj(title=field("title"), detail=field("detail"))))
