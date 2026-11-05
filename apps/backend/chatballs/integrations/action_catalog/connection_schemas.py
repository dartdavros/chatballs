"""Named transport/AI connection fields; credentials are input-only."""

from dataclasses import replace

from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.schema import TypeSpec
from chatballs.integrations.models import IntegrationProvider


def field(name, kind="string", **kwargs):
    if kind == "string" and name in {"description", "greeting", "consentText"}:
        kwargs.setdefault("control", "textarea@1")
    return TypeSpec(kind, title_key=f"native.connection_fields.{name}", **kwargs)


def named(name, spec):
    return replace(spec, title_key=f"native.connection_fields.{name}")


ID = field("integration", "integer", required=True)
PROVIDER = named("provider", enum(IntegrationProvider.values, "native.connection_provider"))
STATUS = named("status", enum(("UNCHECKED", "OK", "ERROR"), "native.agent_status"))
CHANNEL = obj(id=field("channel", "integer"), code=field("code"), name=field("name"),
    groupId=field("group", "integer", nullable=True), hasAgent=field("hasAgent", "boolean"), shared=field("shared", "boolean"))
CONFIG_FIELDS = {key: field(key) for key in ("baseUrl", "defaultModel", "transcriptionModel", "proxyUrl", "botId",
    "botUsername", "botName", "purpose", "title", "accent", "greeting", "consentText", "consentVersion",
    "email", "imapHost", "smtpHost", "folderId")}
CONFIG_FIELDS.update({key: field(key, "integer") for key in ("imapPort", "smtpPort", "maxRecordingBytes", "maxDictationSeconds")})
CONFIG_FIELDS.update({key: field(key, "boolean") for key in ("imapSsl", "smtpSsl", "answerPlaybackEnabled")})
CONFIG_FIELDS.update(allowedOrigins=field("allowedOrigins", "array", items=TypeSpec("string")),
    quickReplies=field("quickReplies", "array", items=TypeSpec("string")),
    preChat=field("preChat", "json"), fields=field("fields", "array", items=TypeSpec("json")),
    appearance=field("appearance", "json", nullable=True),
    siteEvent=field("siteEvent", "json", nullable=True),
    microphoneMode=named("microphoneMode", enum(("off", "voice_message", "dictation"), "native.connection_microphone")))
CONFIG = obj(**CONFIG_FIELDS, siteEventAvailable=field("siteEventAvailable", "boolean"))
HEADER = obj(name=field("name"), secret=field("isSecret", "boolean"), value=field("value", secret=True))
EXTERNAL_INPUT = obj(description=field("description"), url=field("url"),
    headers=field("headers", "array", items=HEADER), toolName=field("toolName"),
    method=named("method", enum(("GET", "POST"), "native.connection_method")),
    readOnly=field("readOnly", "boolean"), parameters=field("parameters", "array", items=TypeSpec("json")))
EDIT = dict(name=field("name"), secret=field("secret", secret=True),
    config=named("config", obj(**{**CONFIG_FIELDS, "proxyUrl": field("proxyUrl", secret=True)})),
    channelId=field("channel", "integer", nullable=True), groupId=field("group", "integer", nullable=True),
    isActive=field("isActive", "boolean"), externalServer=named("externalServer", EXTERNAL_INPUT))
CREATE = obj(**{**EDIT, "name": replace(EDIT["name"], required=True)}, provider=replace(PROVIDER, required=True))
UPDATE = obj(integration_id=ID, **EDIT)
WIDGET = obj(id=field("widget", "integer"), code=field("code"), publicKey=field("publicKey"), name=field("name"),
    status=named("status", enum(("DRAFT", "PUBLISHED", "DISABLED", "ARCHIVED"), "native.connection_widget_status")),
    channel=replace(named("channel", CHANNEL), nullable=True))
CONNECTION = obj(id=field("integration", "integer"), name=field("name"), provider=PROVIDER,
    kind=named("kind", enum(("LLM_PROVIDER", "MESSENGER", "EXTERNAL_SERVER", "SERVICE", "SPEECH_PROVIDER"), "native.connection_kind")),
    hasSecret=field("hasSecret", "boolean"), secretMasked=field("secretMasked"),
    isActive=field("isActive", "boolean"), config=named("config", CONFIG),
    channel=replace(named("channel", CHANNEL), nullable=True), status=STATUS,
    lastCheckedAt=field("lastCheckedAt", "datetime", nullable=True), lastError=field("lastError"),
    createdAt=field("createdAt", "datetime"), updatedAt=field("updatedAt", "datetime"),
    webChatWidget=replace(named("widget", WIDGET), nullable=True), externalServer=field("externalServer", "json"),
    speechCapabilities=field("speechCapabilities", "json"), ttsCheck=field("ttsCheck", "json"))
OUTPUT = obj(integration=named("integration", CONNECTION))
LIST = obj(items=field("connections", "array", items=CONNECTION))
