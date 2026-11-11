"""Scenario management inputs and safe metadata outputs."""

from dataclasses import replace

from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.schema import TypeSpec


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.scenario_fields.{name}", **kwargs)


def named(name, spec):
    return replace(spec, title_key=f"native.scenario_fields.{name}")


ID = field("scenario", required=True)
REVISION = field("revision", "integer", required=True)
SETTINGS = field("definition", "json", required=True, secret=True, control="scenario_settings@1")
POLICY = obj(agent=field("agent", "integer", required=True),
    mode=replace(named("mode", enum(("off", "self", "ask"), "native.scenario_mode")), required=True), revision=REVISION)
POLICIES = field("agentPolicies", "array", items=POLICY)
CATEGORY_PATH = field("categoryPath", "array", items=TypeSpec("string"))
CREATE = obj(name=field("name", required=True), settings=SETTINGS,
    enabled=field("enabled", "boolean"), categoryPath=CATEGORY_PATH)
UPDATE = obj(public_id=ID, revision=REVISION, **dict(CREATE.properties))
ISSUE = obj(path=field("path"), code=field("issueCode"), message=field("message"))
ISSUES = field("issues", "array", items=ISSUE)
KEY = obj(id=field("keyId"), trigger=field("trigger"), url=field("url"))
SCENARIO = obj(id=field("scenario"), name=field("name"), revision=field("revision", "integer"),
    enabled=field("enabled", "boolean"), origin=field("origin", "json"), categoryPath=CATEGORY_PATH,
    connections=field("connections", "array", items=TypeSpec("integer")),
    updatedAt=field("updatedAt", "datetime"), triggers=field("triggers", "array", items=TypeSpec("string")),
    nativeEvents=field("nativeEvents", "array", items=TypeSpec("string")), accessScope=field("accessScope"),
    automationError=field("automationError"), definition=field("definition", "json"),
    agentPolicies=POLICIES, issues=ISSUES, externalKeys=field("externalKeys", "array", items=KEY))
OUTPUT = obj(scenario=named("scenario", SCENARIO))
LIST = obj(items=field("scenarios", "array", items=SCENARIO))
CATALOG = obj(**{key: field(key, "json") for key in ("transforms", "timezone", "labels", "channels",
    "groups", "staff", "agents", "files", "events", "context", "entities", "nativeActions", "scenarios")})
