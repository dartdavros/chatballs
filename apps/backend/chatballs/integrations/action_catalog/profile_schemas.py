"""Personal outputs describe the existing profile and session responses."""

from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.schema import TypeSpec


def field(name, kind="string", **kwargs):
    return TypeSpec(kind, title_key=f"native.personal.{name}", **kwargs)


GROUPS = field("groups", "array", items=obj(id=field("id", "integer"), name=field("name")))
STRINGS = TypeSpec("array", items=TypeSpec("string"))
MEMBERSHIP = obj(id=field("id", "integer"), organizationPublicId=field("organizationPublicId"),
    organization=field("organization"), organizationName=field("organizationName"),
    organizationLogoUrl=field("organizationLogoUrl", nullable=True), role=field("role"),
    positionTitle=field("positionTitle"), totpRequired=field("totpRequired", "boolean"),
    joinedAt=field("joinedAt", "datetime"), capabilities=STRINGS, groups=GROUPS,
    supervisedGroups=GROUPS, supervisionCapabilities=STRINGS, reportCapabilities=STRINGS)
USER = obj(id=field("id", "integer"), email=field("email"), fullName=field("fullName"),
    mustChangePassword=field("mustChangePassword", "boolean"), totpEnabled=field("totpEnabled", "boolean"),
    totpLastUsedAt=field("totpLastUsedAt", "datetime", nullable=True), deliveryMode=field("deliveryMode"),
    uiTheme=field("uiTheme"), uiAccent=field("uiAccent"), uiLanguage=field("uiLanguage"), language=field("language"),
    avatarUrl=field("avatarUrl", nullable=True), isInstanceAdmin=field("isInstanceAdmin", "boolean"),
    memberships=field("memberships", "array", items=MEMBERSHIP))
OUTPUT = obj(authenticated=field("authenticated", "boolean"), user=USER)
SESSIONS = obj(items=field("items", "array", items=obj(id=field("id"), device=field("device"),
    kind=field("kind"), address=field("address"), startedAt=field("startedAt", "datetime", nullable=True),
    lastSeenAt=field("lastSeenAt", "datetime", nullable=True), current=field("current", "boolean"))))
