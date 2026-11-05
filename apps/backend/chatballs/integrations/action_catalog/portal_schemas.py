"""Portal settings and category contracts for the common editor."""

from dataclasses import replace

from chatballs.integrations.action_catalog.pagination import PAGE_INPUTS, page_of
from chatballs.integrations.action_catalog.schema import enum, obj
from chatballs.integrations.adapters.schema import TypeSpec


def field(name, kind="string", **kwargs):
    if kind == "string" and name in {"content", "summary", "description"}:
        kwargs.setdefault("control", "textarea@1")
    return TypeSpec(kind, title_key=f"native.portal_fields.{name}", **kwargs)


def named(name, spec, **kwargs):
    return replace(spec, title_key=f"native.portal_fields.{name}", **kwargs)


def choice(name, values):
    return named(name, enum(values, f"native.portal_{name}"))


ID = field("portal", "integer", required=True)
STATUS = choice("status", ("DRAFT", "PUBLISHED", "ARCHIVED"))
EDIT = dict(slug=field("slug"), name=field("name"), defaultLocale=field("defaultLocale"),
    widgetId=field("widget", "integer", nullable=True), widgetChannelId=field("agent", "integer", nullable=True),
    theme=field("theme"), themeScheme=choice("themeScheme", ("LIGHT", "DARK", "SYSTEM")),
    themeSettings=field("themeSettings", "object", open=True))
PORTAL = obj(**EDIT, id=field("portal", "integer"), publicId=field("publicId"),
    hostedDomain=field("hostedDomain"), customDomain=field("customDomain", nullable=True),
    customDomainAddress=named("customDomainAddress", obj(name=field("name"), type=field("recordType"),
        value=field("address")), nullable=True),
    customDomainVerifiedAt=field("customDomainVerifiedAt", "datetime", nullable=True),
    publicUrl=field("publicUrl"), status=STATUS, publishedAt=field("publishedAt", "datetime", nullable=True),
    widgetKey=field("widgetKey", nullable=True), widgetChannelCode=field("agentCode", nullable=True),
    createdAt=field("createdAt", "datetime"), updatedAt=field("updatedAt", "datetime"),
    categoryCount=field("categoryCount", "integer"), articleCount=field("articleCount", "integer"))
OUTPUT = obj(portal=named("portal", PORTAL))
PAGE = replace(page_of(PORTAL), properties=page_of(PORTAL).properties + (
    ("creation", named("creation", obj(available=field("available", "boolean"), canCreate=field("canCreate", "boolean"),
        limit=field("limit", "integer", nullable=True), used=field("used", "integer")))),
    ("address", named("address", obj(scheme=field("scheme"), baseDomain=field("baseDomain"),
        port=field("port", nullable=True)))),))
FILTERS = obj(**PAGE_INPUTS, q=field("search"), status=field("status", "array", items=STATUS))
WIDGET = obj(id=field("widget", "integer"), code=field("code"), publicKey=field("widgetKey"), name=field("name"),
    status=STATUS, channel=named("agent", obj(id=field("agent", "integer"), code=field("agentCode"), name=field("name")), nullable=True))
CATEGORY_EDIT = dict(name=field("name"), slug=field("slug"), description=field("description"),
    parentId=field("parent", "integer", nullable=True), sortOrder=field("sortOrder", "integer"))
CATEGORY = obj(**CATEGORY_EDIT, id=field("category", "integer"), articleCount=field("articleCount", "integer"))
CATEGORY_ID = field("category", "integer", required=True)
