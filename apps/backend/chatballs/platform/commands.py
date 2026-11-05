"""Provisioning command shared by the platform API and its native descriptor."""
from chatballs.i18n import t
from chatballs.identity.command_outcomes import CommandOutcome
from chatballs.identity.models import EmployeeRole, OrganizationMembership
from chatballs.integrations.action_catalog.authority import require_platform
from chatballs.platform.errors import ProvisioningError
from chatballs.platform.models import ProvisioningSource
from chatballs.platform.payloads import owner_state_for, provisioning_result_payload
from chatballs.platform.provisioning_service import provision_organization
from chatballs.platform.validation import parse_provisioning_body
from chatballs.tenancy.database import tenant_atomic


def provision(operator, token, body, *, idempotency_key):
    operator = require_platform(operator, token, "platform.organizations.provision")
    idempotency_key = str(idempotency_key).strip()
    if not idempotency_key:
        return CommandOutcome({"detail": t("platform.idempotency_key_required")}, status=400)
    command, error = parse_provisioning_body(
        body,
        idempotency_key=idempotency_key,
        source=ProvisioningSource.PLATFORM_OPERATOR,
    )
    if error:
        return CommandOutcome({"detail": error}, status=400)
    try:
        result = provision_organization(command=command, operator=operator)
    except ProvisioningError as error:
        return CommandOutcome({"detail": str(error)}, status=error.status_code)
    # Членство — тенантная строка: под ролью platform без tenant-контекста
    # RLS её не покажет, и ответ назвал бы активного владельца ожидающим.
    with tenant_atomic(result.organization.pk):
        owner_membership = OrganizationMembership.objects.filter(
            organization=result.organization, role=EmployeeRole.OWNER
        ).first()
    payload = provisioning_result_payload(
        provisioning=result.provisioning,
        organization=result.organization,
        owner_state=owner_state_for(result.organization, owner_membership),
    )
    status_code = 201 if result.created else 200
    return CommandOutcome(payload, status=status_code)
