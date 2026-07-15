from __future__ import annotations

from rest_framework.test import APIClient

from hub_platform.identity.models import HumanUser, Organization, OrganizationMembership
from hub_platform.tenancy.context import TenantActorKind, TenantContext


def tenant_context_for(
    user: HumanUser,
    organization: Organization | None = None,
) -> TenantContext:
    memberships = OrganizationMembership.objects.select_related("organization", "user").filter(
        user=user,
        blocked_at__isnull=True,
    )
    if organization is not None:
        memberships = memberships.filter(organization=organization)
    return TenantContext.for_membership(memberships.get())


def system_tenant_context(organization: Organization) -> TenantContext:
    return TenantContext.for_resource(organization, actor_kind=TenantActorKind.SYSTEM)


class TenantAPIClient(APIClient):
    """Test client that turns legacy test literals into the C03 tenant route.

    Production URL resolution is untouched. New tenancy tests call canonical URLs
    directly and assert that the old runtime routes return 404.
    """

    tenant_namespaces = {
        "access-profiles",
        "ai",
        "calls",
        "channels",
        "company",
        "conversations",
        "employees",
        "integrations",
        "notifications",
        "orders",
        "sales",
        "support",
    }
    public_prefixes = (
        "/api/v1/ai/files/",
        "/api/v1/calls/access/",
        "/api/v1/calls/invites/",
        "/api/v1/orders/ingest/",
        "/api/v1/support/sessions/",
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._tenant_user = None
        self.organization_public_id = None

    def force_authenticate(self, user=None, token=None) -> None:
        self._tenant_user = user
        if user is not None:
            # Tenant middleware runs before DRF's force-auth hook, so test
            # requests also need Django's authenticated session available.
            super().force_login(user)
        super().force_authenticate(user=user, token=token)

    def login(self, **credentials) -> bool:
        authenticated = super().login(**credentials)
        if authenticated:
            email = credentials.get("email") or credentials.get("username")
            self._tenant_user = HumanUser.objects.filter(email=email).first()
        return authenticated

    def force_login(self, user, backend=None) -> None:
        self._tenant_user = user
        super().force_login(user, backend=backend)

    def logout(self) -> None:
        self._tenant_user = None
        super().logout()

    def set_tenant(self, organization) -> None:
        self.organization_public_id = organization.public_id

    def generic(self, method, path, data="", content_type="application/octet-stream", secure=False, **extra):
        path = self._organization_path(path)
        return super().generic(method, path, data, content_type, secure, **extra)

    def _organization_path(self, path: str) -> str:
        if not path.startswith("/api/v1/") or path.startswith("/api/v1/organizations/"):
            return path
        if any(path.startswith(prefix) for prefix in self.public_prefixes):
            return path
        namespace = path[len("/api/v1/") :].split("/", 1)[0]
        if namespace not in self.tenant_namespaces:
            return path
        public_id = self.organization_public_id
        if public_id is None and self._tenant_user is not None:
            values = list(
                self._tenant_user.memberships.filter(blocked_at__isnull=True).values_list(
                    "organization__public_id", flat=True
                )[:2]
            )
            public_id = values[0] if len(values) == 1 else None
        if public_id is None:
            return path
        return f"/api/v1/organizations/{public_id}{path[len('/api/v1') :]}"
