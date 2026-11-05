"""Test-chat input and lossless typed output from the existing AI runtime."""

from chatballs.integrations.action_catalog.agent_schemas import ID, choice, field
from chatballs.integrations.action_catalog.schema import obj

INPUT = obj(agent_id=ID, message=field("message", required=True),
    executionMode=choice("executionMode", ("preview", "execute")),
    history=field("history", "array", items=obj(role=choice("role", ("user", "assistant")), content=field("content"))),
    clientData=field("clientData", "object", properties=obj(name=field("name"), email=field("email"), phone=field("phone"),
        webFields=field("webFields", "object", open=True)).properties))
OUTPUT = obj(reply=field("reply"), model=field("model"),
    promptTokens=field("promptTokens", "integer"), completionTokens=field("completionTokens", "integer"),
    toolCalls=field("toolCalls", "array", items=obj(name=field("toolName"), tool=field("title"),
        ok=field("ok", "boolean"), errorCode=field("lastErrorCode"), error=field("lastError"),
        durationMs=field("durationMs", "integer"), turnId=field("turnId", "integer", nullable=True))),
    skillSupport=choice("skillSupport", ("unknown", "supported", "unsupported")), skillWarning=field("skillWarning"),
    serviceActions=field("serviceActions", "array", items=field("serviceAction", "object", open=True)),
    formatVersion=field("formatVersion", "integer"), contentHtml=field("contentHtml"),
    presentation=field("presentation", "object", open=True), deliveryRepresentation=field("deliveryRepresentation"),
    template=field("template", "object", open=True))
