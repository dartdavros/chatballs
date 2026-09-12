from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chatballs.i18n import t
from chatballs.identity.models import EmployeeRole, OrganizationMembership
from chatballs.platform.authentication import PlatformTokenAuthentication
from chatballs.platform.errors import ProvisioningError
from chatballs.platform.models import ProvisioningSource
from chatballs.platform.payloads import owner_state_for, provisioning_result_payload
from chatballs.platform.permissions import HasPlatformCapability
from chatballs.platform.provisioning_service import provision_organization
from chatballs.platform.validation import parse_provisioning_body

_IDEMPOTENCY_HEADER = "Idempotency-Key"


class OrganizationProvisionView(APIView):
    """POST <platform-host>/api/v1/organizations (SPEC-HUB-0021 §12).

    The first Platform API adapter: machine-to-machine provisioning via an
    opaque platform token. Does not reuse tenant HasCapability (no membership
    exists yet) and is not reachable on the app surface.
    """

    authentication_classes = [PlatformTokenAuthentication]
    permission_classes = [HasPlatformCapability]
    required_platform_capability = "platform.organizations.provision"

    def post(self, request: Request) -> Response:
        idempotency_key = request.headers.get(_IDEMPOTENCY_HEADER, "").strip()
        if not idempotency_key:
            return Response({"detail": t("platform.idempotency_key_required")}, status=400)
        command, error = parse_provisioning_body(
            request.data,
            idempotency_key=idempotency_key,
            source=ProvisioningSource.PLATFORM_OPERATOR,
        )
        if error:
            return Response({"detail": error}, status=400)
        try:
            result = provision_organization(command=command, operator=request.user)
        except ProvisioningError as error:
            return Response({"detail": str(error)}, status=error.status_code)
        owner_membership = OrganizationMembership.objects.filter(
            organization=result.organization, role=EmployeeRole.OWNER
        ).first()
        payload = provisioning_result_payload(
            provisioning=result.provisioning,
            organization=result.organization,
            owner_state=owner_state_for(result.organization, owner_membership),
        )
        status_code = 201 if result.created else 200
        return Response(payload, status=status_code)
