"""Named agent card, directory and configuration contracts."""

from dataclasses import replace

from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.schema import TypeSpec


def field(name, kind="string", **kwargs):
    if kind == "string" and name in {"persona", "tone", "instructions", "description"}:
        kwargs.setdefault("control", "textarea@1")
    return TypeSpec(kind, title_key=f"native.agent_fields.{name}", **kwargs)


def choice(name, values):
    return replace(enum(values, f"native.agent_{name}"), title_key=f"native.agent_fields.{name}")


ID = field("agent", "integer", required=True)
STATUS = choice("aiStatus", ("DRAFT", "ACTIVE", "DISABLED", "ARCHIVED"))
CONNECTION_STATUS = choice("status", ("UNCHECKED", "OK", "ERROR"))
TOOL_SELECTION = obj(integrationId=field("integrationId", "integer", required=True), name=field("toolName"))
EDIT = dict(name=field("name"), groupId=field("groupId", "integer", nullable=True),
    isActive=field("isActive", "boolean"),
    providerIntegrationId=field("providerIntegrationId", "integer", nullable=True),
    transcriptionIntegrationId=field("transcriptionIntegrationId", "integer", nullable=True),
    transcriptionLanguage=choice("transcriptionLanguage", ("", "ru-RU", "en-US")),
    synthesisIntegrationId=field("synthesisIntegrationId", "integer", nullable=True),
    synthesisModel=field("synthesisModel"), synthesisVoice=field("synthesisVoice"),
    **{key: field(key) for key in ("model", "transcriptionModel", "persona", "tone", "instructions")},
    modelParams=field("modelParams", "object", open=True),
    answerLanguage=choice("answerLanguage", ("MIRROR", "ORGANIZATION", "ru", "en")),
    historyLimit=field("historyLimit", "integer"), assistanceEnabled=field("assistanceEnabled", "boolean"),
    knowledgeIds=field("knowledge", "array", items=TypeSpec("integer")),
    tools=field("tools", "array", items=TOOL_SELECTION))
TOOL = obj(name=field("toolName"), title=field("title"), description=field("description"),
    readOnly=field("readOnly", "boolean"), enabled=field("enabled", "boolean"))
SERVER = obj(integrationId=field("integrationId", "integer"), name=field("name"),
    type=choice("type", ("mcp", "http")), isActive=field("isActive", "boolean"), status=CONNECTION_STATUS,
    lastError=field("lastError"), lastErrorCode=field("lastErrorCode"),
    lastCheckedAt=field("lastCheckedAt", "datetime", nullable=True), tools=field("tools", "array", items=TOOL))
TOOLS = field("tools", "array", items=SERVER)
CONNECTION = obj(id=field("integrationId", "integer"), name=field("name"),
    provider=choice("provider", ("MAX", "TELEGRAM", "VK", "WEB", "EMAIL")), status=CONNECTION_STATUS,
    botUsername=field("botUsername"), email=field("email"),
    allowedOrigins=field("allowedOrigins", "array", items=TypeSpec("string")), widgetPublicKey=field("widgetPublicKey"))
KNOWLEDGE = obj(id=field("knowledge", "integer"), title=field("title"),
    isEnabled=field("enabled", "boolean"), updatedAt=field("updatedAt", "datetime"))
ARTICLE = obj(id=field("article", "integer"), title=field("title"),
    status=choice("articleStatus", ("DRAFT", "PUBLISHED", "ARCHIVED")),
    portal=field("portal", "object", properties=obj(id=field("portal", "integer"), name=field("name")).properties),
    publicUrl=field("publicUrl", nullable=True))
CARD = obj(**{key: value for key, value in EDIT.items() if key not in {"knowledgeIds", "tools"}},
    id=field("agent", "integer"), aiAgentId=field("aiAgentId", "integer"), code=field("code"),
    groupName=field("groupName", nullable=True), groupColor=field("groupColor"), aiStatus=STATUS,
    providerModel=field("providerModel"), transcriptionProviderModel=field("transcriptionProviderModel"),
    modelSupportsTools=field("modelSupportsTools", "boolean", nullable=True),
    knowledge=field("knowledge", "array", items=KNOWLEDGE), knowledgeTotal=field("knowledgeTotal", "integer"),
    portalArticles=field("portalArticles", "array", items=ARTICLE),
    connections=field("connections", "array", items=CONNECTION), tools=TOOLS,
    counters=field("counters", "object", properties=obj(openConversations=field("openConversations", "integer"),
        connections=field("connections", "integer")).properties),
    createdAt=field("createdAt", "datetime"), updatedAt=field("updatedAt", "datetime"))
OUTPUT = obj(agent=replace(CARD, title_key="native.agent_fields.agent"))
PAGE = page_of(CARD)
FILTERS = obj(**PAGE_INPUTS, q=field("search"), group=field("groupFilter"))
DIRECTORY = obj(items=field("agents", "array", items=obj(id=field("agent", "integer"),
    aiAgentId=field("aiAgentId", "integer", nullable=True), name=field("name"),
    groupName=field("groupName", nullable=True), aiStatus=replace(STATUS, nullable=True),
    isActive=field("isActive", "boolean"), knowledgeCount=field("knowledgeTotal", "integer"))),
    hasMore=field("hasMore", "boolean"))
