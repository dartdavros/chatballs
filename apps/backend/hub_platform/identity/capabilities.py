from __future__ import annotations

from dataclasses import dataclass


class ScopeType:
    ORGANIZATION = "ORGANIZATION"
    DEPARTMENT = "DEPARTMENT"


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    code: str
    name: str
    description: str
    allowed_scopes: frozenset[str]
    assignable: bool = True
    protected: bool = False


_ALL_SCOPES = frozenset({ScopeType.ORGANIZATION, ScopeType.DEPARTMENT})
_ORGANIZATION_ONLY = frozenset({ScopeType.ORGANIZATION})


def _capability(
    code: str,
    name: str,
    *,
    scopes: frozenset[str] = _ALL_SCOPES,
    assignable: bool = True,
    protected: bool = False,
) -> CapabilitySpec:
    return CapabilitySpec(
        code=code,
        name=name,
        description=name,
        allowed_scopes=scopes,
        assignable=assignable,
        protected=protected,
    )


# SPEC-HUB-0017 §5.2. The registry is application code, never database data.
CAPABILITY_REGISTRY = {
    item.code: item
    for item in (
        _capability("company.view", "View company", scopes=_ORGANIZATION_ONLY),
        _capability("company.manage", "Manage company", scopes=_ORGANIZATION_ONLY),
        _capability("departments.view", "View departments"),
        _capability("departments.manage", "Manage departments", scopes=_ORGANIZATION_ONLY),
        _capability("employees.view", "View employees"),
        _capability("employees.manage", "Manage employees", scopes=_ORGANIZATION_ONLY),
        _capability(
            "employees.manage_privileged",
            "Manage privileged employees",
            scopes=_ORGANIZATION_ONLY,
            assignable=False,
            protected=True,
        ),
        _capability(
            "ownership.transfer",
            "Transfer ownership",
            scopes=_ORGANIZATION_ONLY,
            assignable=False,
            protected=True,
        ),
        _capability("products.view", "View products"),
        _capability("products.manage", "Manage products"),
        _capability("ai.view", "View AI configuration", scopes=_ORGANIZATION_ONLY),
        _capability("ai.manage", "Manage AI configuration", scopes=_ORGANIZATION_ONLY),
        _capability("ai.publish", "Publish AI configuration", scopes=_ORGANIZATION_ONLY),
        _capability("integrations.view", "View integrations", scopes=_ORGANIZATION_ONLY),
        _capability("integrations.manage", "Manage integrations", scopes=_ORGANIZATION_ONLY),
        _capability("secrets.manage", "Manage secrets", scopes=_ORGANIZATION_ONLY),
        _capability("settings.view", "View settings", scopes=_ORGANIZATION_ONLY),
        _capability("settings.manage", "Manage settings", scopes=_ORGANIZATION_ONLY),
        _capability("audit.view", "View audit", scopes=_ORGANIZATION_ONLY),
        _capability("conversations.view", "View conversations"),
        _capability("conversations.operate", "Operate conversations"),
        _capability("conversations.call", "Create calls"),
        _capability("customers.view", "View customers"),
        _capability("customers.manage", "Manage customers"),
        _capability("sales.view", "View sales"),
        _capability("sales.operate", "Operate sales"),
        _capability("sales.correct", "Correct sales"),
        _capability("sales_sources.manage", "Manage sales sources", scopes=_ORGANIZATION_ONLY),
        _capability("support.view", "View support"),
        _capability("support.operate", "Operate support"),
        _capability("notifications.manage", "Manage notifications", scopes=_ORGANIZATION_ONLY),
    )
}

PROTECTED_CAPABILITIES = frozenset(
    code for code, spec in CAPABILITY_REGISTRY.items() if spec.protected
)


def capability_spec(code: str) -> CapabilitySpec:
    try:
        return CAPABILITY_REGISTRY[code]
    except KeyError as error:
        raise ValueError(f"Unknown capability: {code}") from error

