"""Creating an organization preserves the authenticated caller's global policy."""

from chatballs.identity import organization_commands
from chatballs.integrations.action_catalog.administrative import register
from chatballs.integrations.action_catalog.profile_schemas import USER, field
from chatballs.integrations.action_catalog.schema import obj
from chatballs.integrations.adapters.contracts import Effect
from chatballs.integrations.adapters.schema import TypeSpec

OPTION = obj(code=field("code"), label=field("name"))
OPTIONS = obj(timezones=field("timezones", "array", items=TypeSpec("string")),
    languages=field("languages", "array", items=OPTION), currencies=field("currencies", "array", items=TypeSpec("string")))

for key, route, view, method, inputs, outputs, service, body, effect in (
    ("organizations.options.get", "options/", "OrganizationCreateOptionsView", "GET", obj(), OPTIONS, organization_commands.options, False, Effect.READ),
    ("organizations.post", "", "OrganizationCreateView", "POST", obj(name=field("name", required=True), timezone=field("timezone"), language=field("language")), obj(user=USER, organizationPublicId=field("organizationPublicId")), organization_commands.create, True, Effect.CREATE),
):
    register(key=key, inputs=inputs, outputs=outputs, service=service, body=body, authority="personal",
        route=f"api/v1/organizations/{route}", view=f"chatballs.identity.organization_views.{view}", method=method, effect=effect)
