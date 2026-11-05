"""Closed installation settings schemas; no credentials in output."""

from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.schema import TypeSpec


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.installation.{name}", **kwargs)


EMAIL_INPUT = obj(host=field("host"), port=field("port", "integer"), user=field("user"),
    password=field("password", secret=True), useTls=field("useTls", "boolean"), **{"from": field("from")})
EMAIL_OUTPUT = obj(host=field("host"), port=field("port", "integer"), user=field("user"),
    hasPassword=field("hasPassword", "boolean"), useTls=field("useTls", "boolean"),
    configured=field("configured", "boolean"), **{"from": field("from")})
TURN_INPUT = obj(urls=field("urls", "array", items=TypeSpec("string")), ttlSeconds=field("ttlSeconds", "integer"))
TURN_OUTPUT = obj(**dict(TURN_INPUT.properties), secretReady=field("secretReady", "boolean"))
INPUT = obj(publicHost=field("publicHost"), publicScheme=field("publicScheme"),
    defaultLanguage=field("defaultLanguage"), email=EMAIL_INPUT, turn=TURN_INPUT)
OUTPUT = obj(instance=obj(publicHost=field("publicHost"), publicScheme=field("publicScheme"),
    publicUrl=field("publicUrl"), defaultLanguage=field("defaultLanguage"),
    languages=field("languages", "array", items=obj(code=field("code"), label=field("label"))),
    updatedAt=field("updatedAt", "datetime", nullable=True), email=EMAIL_OUTPUT, turn=TURN_OUTPUT))
NETWORK = obj(toolsNetwork=obj(enabled=field("enabled", "boolean"),
    enabledBy=TypeSpec("object", title_key="native.installation.enabledBy", nullable=True,
        properties=obj(id=field("id", "integer"), name=field("name")).properties),
    enabledAt=field("enabledAt", "datetime", nullable=True)))
