"""Widget asset application boundary, shared by HTTP and scenario actions."""

from django.core.exceptions import ValidationError

from chatballs.i18n import t
from chatballs.integrations.models import Integration, IntegrationProvider
from chatballs.integrations.selectors import integration_for_context
from chatballs.integrations.service_connections.management import audit
from chatballs.integrations.service_connections.management_reads import require
from chatballs.tenancy.context import TenantContext
from chatballs.tenancy.database import tenant_atomic
from chatballs.tenancy.ingress import widget_asset_route
from chatballs.tenancy.lookup import load_organization
from chatballs.webchat.assets import upload_widget_asset, widget_asset_url
from chatballs.webchat.models import WidgetAsset


def upload(context, integration_id, file, *, request=None):
    require(context, "integrations.manage")
    with tenant_atomic(context):
        row = integration_for_context(context=context, integration_id=integration_id)
        if row.provider != IntegrationProvider.WEB:
            raise Integration.DoesNotExist()
        if file is None:
            raise ValidationError({"file": t("webchat.asset_choose_file")})
        asset = upload_widget_asset(context=context, integration=row, upload=file, uploaded_by=context.actor_user)
        audit(context, "integrations.widget_asset_uploaded", row.pk, request=request)
        return {"url": widget_asset_url(asset)}


def open_asset(public_id, *, organization_id=None):
    route = widget_asset_route(str(public_id))
    if route is None or organization_id is not None and route.organization_id != organization_id:
        raise WidgetAsset.DoesNotExist()
    organization = load_organization(route.organization_id)
    if organization is None:
        raise WidgetAsset.DoesNotExist()
    with tenant_atomic(TenantContext.for_resource(organization)):
        row = WidgetAsset.objects.get(id=route.resource_id, public_id=public_id, organization=organization)
        return row.file.open("rb"), row.file.name.rsplit("/", 1)[-1], row.content_type
