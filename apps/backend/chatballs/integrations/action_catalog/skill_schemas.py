"""Skill configuration and renderer contracts for the common action editor."""

from dataclasses import replace

from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import obj, required
from chatballs.integrations.adapters.schema import TypeSpec


def field(name, kind="string", **kwargs):
    if kind == "string" and name in {"description", "instruction", "html", "css", "text", "purpose"}:
        kwargs.setdefault("control", "textarea@1")
    return TypeSpec(kind, title_key=f"native.skill_fields.{name}", **kwargs)


def named(name, value, **kwargs):
    return replace(value, title_key=f"native.skill_fields.{name}", **kwargs)


ID = field("skill", required=True)
REVISION = field("revision", "integer", required=True)
DATA = field("data", "object", open=True)
TEMPLATE = obj(id=field("templateId"), name=field("name"), purpose=field("purpose"),
    schema=field("schema", "object", open=True), html=field("html"), css=field("css"), text=field("text"),
    examples=field("examples", "array", items=TypeSpec("json", nullable=True, control="structured_value@1")),
    exampleNames=field("exampleNames", "array", items=TypeSpec("string")))
CONFIGURATION = obj(name=field("name", required=True), description=field("description", required=True),
    instruction=field("instruction", required=True),
    templates=field("templates", "array", required=True, items=TEMPLATE))
AUTHOR = obj(id=field("author", "integer"), name=field("name"))
SKILL = obj(**dict(CONFIGURATION.properties), id=field("skill"), revision=field("revision", "integer"),
    templateCount=field("templateCount", "integer"), agentCount=field("agentCount", "integer"),
    agents=field("agents", "array", items=obj(id=field("agent", "integer"),
        aiAgentId=field("aiAgentId", "integer"), name=field("name"))),
    createdBy=named("createdBy", AUTHOR, nullable=True), updatedBy=named("updatedBy", AUTHOR, nullable=True),
    createdAt=field("createdAt", "datetime"), updatedAt=field("updatedAt", "datetime"))
# Summary payloads deliberately omit instruction and template source.
SUMMARY = replace(SKILL, properties=tuple((key, replace(spec, required=False)) for key, spec in SKILL.properties))
OUTPUT = obj(skill=named("skill", SUMMARY))
PAGE = replace(page_of(SUMMARY), properties=page_of(SUMMARY).properties + (
    ("connectedAgentCount", field("connectedAgentCount", "integer")),))
FILTERS = obj(**PAGE_INPUTS, q=field("search"), agentId=field("agentFilter"))
SAVE = dict(requestId=field("requestId", required=True), configuration=named("configuration", CONFIGURATION, required=True))
VALIDATE = obj(configuration=SAVE["configuration"])
PREVIEW = obj(configuration=SAVE["configuration"], templateId=field("templateId", required=True), data=required(DATA))
RENDERED = obj(text=field("text"), contentHtml=field("html"),
    presentation=named("presentation", obj(formatVersion=field("formatVersion", "integer"),
        css=field("css"), isolation=field("isolation"), sandbox=field("sandbox"), srcDoc=field("srcDoc"))))
