from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from hub_platform.identity.audit import record_audit_event
from hub_platform.identity.models import Organization
from hub_platform.sales.models import SalesSource, SalesSourceStatus
from hub_platform.sales.services import (
    SalesApiError,
    hash_credential,
    record_product_sales_event,
)
from hub_platform.tenancy.context import TenantContext
from hub_platform.tenancy.database import tenant_atomic
from hub_platform.tenancy.ingress import sales_source_route


def _api_error(error: SalesApiError) -> Response:
    return Response(
        {"detail": error.message, "error": error.error_code},
        status=error.status_code,
    )


def _bearer(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer ") :].strip()
    return ""


class ProductSalesEventView(APIView):
    """Канонический вход Product Sales API (SPEC-HUB-0014 §4)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        credential = _bearer(request)
        credential_hash = hash_credential(credential) if credential else ""
        route = sales_source_route(credential_hash) if credential_hash else None
        if route is None:
            return self._invalid_credential()
        try:
            organization = Organization.objects.get(pk=route.organization_id)
        except Organization.DoesNotExist:
            return self._invalid_credential()
        context = TenantContext.for_resource(organization)
        with tenant_atomic(context):
            source = SalesSource.objects.select_related(
                "product", "organization"
            ).filter(
                id=route.resource_id,
                organization=organization,
                credential_hash=credential_hash,
                status=SalesSourceStatus.ACTIVE,
            ).first()
            if source is None:
                return self._invalid_credential()
            return self._post_for_source(request, context=context, source=source)

    def _post_for_source(
        self,
        request: Request,
        *,
        context: TenantContext,
        source: SalesSource,
    ) -> Response:
        try:
            result = record_product_sales_event(
                context=context,
                source=source,
                payload=request.data,
            )
        except SalesApiError as error:
            record_audit_event(
                action="sales.event_rejected",
                actor=None,
                organization=source.organization,
                object_type="SalesSource",
                object_id=str(source.id),
                payload={"error": error.error_code},
                request=request,
            )
            return _api_error(error)

        body = {
            "accepted": True,
            "duplicate": result.duplicate,
            "event_id": result.event.external_event_id,
        }
        return Response(body, status=200 if result.duplicate else 202)

    @staticmethod
    def _invalid_credential() -> Response:
        return Response(
            {
                "detail": "Invalid or revoked credential",
                "error": "invalid_credential",
            },
            status=401,
        )
