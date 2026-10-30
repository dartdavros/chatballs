from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError

from chatballs.i18n import t
from chatballs.integrations.adapters.files import discard_service_files
from chatballs.integrations.models import Integration
from chatballs.tenancy.context import TenantContext
from chatballs.webchat.assets import discard_widget_asset_files, widget_asset_files


class IntegrationInUse(Exception):
    """Интеграция связана с агентом или каналом и не может быть удалена."""


def delete_integration(*, context: TenantContext, integration: Integration) -> None:
    if integration.organization_id != context.organization_id:
        raise ValidationError({"integration": t("settings.integration_other_organization")})
    asset_files = widget_asset_files(integration)
    try:
        discard_service_files(context=context, integration=integration)
        integration.delete()
    except ProtectedError as error:
        raise IntegrationInUse(t("settings.integration_in_use")) from error
    discard_widget_asset_files(context=context, files=asset_files)
