"""Global organization creation: caller identity is never a tenant delegate."""
from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.identity.administration_payloads import (
    administration_languages,
    administration_timezones,
)
from chatballs.identity.administration_services import OrganizationSettingsInput
from chatballs.identity.auth.common import _user_payload
from chatballs.identity.command_outcomes import CommandOutcome, validation_outcome
from chatballs.identity.organization_creation import can_create_organization, create_organization
from chatballs.integrations.action_catalog.authority import current_user


def _forbidden():
    return CommandOutcome({"detail": t("identity.organization_create_forbidden")}, status=403)


def options(user):
    user = current_user(user)
    if not can_create_organization(user):
        return _forbidden()
    return CommandOutcome(
        {
            "timezones": administration_timezones(),
            "languages": administration_languages(),
            "currencies": ["RUB"],
        }
    )


def create(user, body):
    user = current_user(user)
    if not can_create_organization(user):
        return _forbidden()
    body = body if isinstance(body, dict) else {}
    try:
        created = create_organization(
            data=OrganizationSettingsInput(
                name=str(body.get("name", "")),
                timezone=str(body.get("timezone", "") or "Europe/Moscow"),
                language=str(body.get("language", "")),
            ),
            owner=user,
        )
    except ValidationError as error:
        return validation_outcome(error)
    return CommandOutcome(
        {
            "user": _user_payload(user),
            "organizationPublicId": str(created.organization.public_id),
        },
        status=201,
    )

