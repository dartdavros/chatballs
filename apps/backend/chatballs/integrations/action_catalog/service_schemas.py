"""Service connection fields; credentials remain write-only inputs."""

from dataclasses import replace

from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.registry import default_registry
from chatballs.integrations.adapters.schema import EnumOption, TypeSpec


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.service_fields.{name}", **kwargs)


ID = field("connection", "integer", required=True)
ERROR = obj(code=field("errorCode", options=(EnumOption("unauthorized", "services.error_unauthorized_title"),),
    placeholder_key="services.error_rejected_title"), title=field("errorTitle"), text=field("errorText"))
STATUS = replace(enum(("ok", "lost", "unchecked"), "native.service_status"),
    title_key="native.service_fields.status")
CONNECTION = obj(id=field("connection", "integer"), name=field("name"), adapter=field("adapter"),
    authMethod=field("authMethod"), status=STATUS, isActive=field("isActive", "boolean"),
    host=field("host"), hasCredentials=field("hasCredentials", "boolean"),
    incompatible=field("incompatible", "boolean"), lastCheckedAt=field("lastCheckedAt", "datetime", nullable=True),
    error=replace(ERROR, title_key="native.service_fields.error", nullable=True),
    scenarios=field("scenarios", "object", properties=obj(enabled=field("enabledScenarios", "integer")).properties),
    createdAt=field("createdAt", "datetime"))
OUTPUT = obj(connection=replace(CONNECTION, title_key="native.service_fields.connection"))
LIST = obj(items=field("connections", "array", items=CONNECTION))
ACCESS = field("values", "object", open=True, secret=True, required=True)
# Presentation comes from installed trusted descriptors. The domain validates
# the selected pair and its credential schema at execution time.
ADAPTERS = tuple(EnumOption(item.key, item.presentation.title_key) for item in default_registry().catalog())
METHODS = tuple({method.key: EnumOption(method.key, method.title_key)
    for adapter in default_registry().catalog() for method in adapter.auth_methods}.values())
CREATE = obj(name=field("name", required=True),
    adapter=field("adapter", "enum" if ADAPTERS else "string", required=True, options=ADAPTERS),
    authMethod=field("authMethod", "enum" if METHODS else "string", required=True, options=METHODS), values=ACCESS)
UPDATE = obj(connection_id=ID, name=field("name"), isActive=field("isActive", "boolean"))
CHECK = obj(connection_id=ID, inputs=field("checkInputs", "object", open=True, secret=True))
REPLACE = obj(connection_id=ID, values=ACCESS)
LOOKUP = obj(connection_id=ID, key=field("lookup", required=True))
LOOKUP_RESULT = obj(items=field("options", "array", items=obj(value=field("value", "json"), label=field("label"))))
CATALOG = obj(items=field("adapters", "array", items=TypeSpec("json")))
