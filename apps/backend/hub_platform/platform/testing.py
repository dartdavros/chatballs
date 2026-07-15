from __future__ import annotations

from hub_platform.platform.capabilities import is_valid_platform_capability
from hub_platform.platform.models import PlatformOperator
from hub_platform.platform.tokens import issue_platform_token
from hub_platform.subscriptions.keys import PlanCode
from hub_platform.subscriptions.models import PlanVersion
from hub_platform.subscriptions.plan_service import publish_plan_version


def create_platform_operator(
    *, name: str = "Test operator", capabilities: list[str] | None = None
) -> tuple[PlatformOperator, str]:
    caps = (
        ["platform.organizations.provision"]
        if capabilities is None
        else capabilities
    )
    for code in caps:
        assert is_valid_platform_capability(code), f"unknown capability {code}"
    operator = PlatformOperator.objects.create(name=name)
    _token, plaintext = issue_platform_token(operator=operator, name="default", capabilities=caps)
    return operator, plaintext


def published_plan_version(plan_code: str = PlanCode.STARTUP) -> PlanVersion:
    version = PlanVersion.objects.get(plan__code=plan_code, version=1)
    return publish_plan_version(version)
