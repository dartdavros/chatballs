class SubscriptionDomainError(Exception):
    code = "subscription_error"


class PolicyUnavailable(SubscriptionDomainError):
    code = "policy_unavailable"


class SubscriptionInactive(SubscriptionDomainError):
    code = "subscription_inactive"


class EntitlementRequired(SubscriptionDomainError):
    code = "entitlement_required"

    def __init__(self, entitlement: str) -> None:
        self.entitlement = entitlement
        super().__init__(f"Entitlement required: {entitlement}")


class QuotaExceeded(SubscriptionDomainError):
    code = "quota_exceeded"

    def __init__(
        self,
        *,
        resource: str,
        limit: int,
        used: int,
        requested: int,
        period_ends_at=None,
        mode: str = "HARD",
    ) -> None:
        self.resource = resource
        self.limit = limit
        self.used = used
        self.requested = requested
        self.period_ends_at = period_ends_at
        self.mode = mode
        super().__init__(f"Quota exceeded: {resource}")


class UsageConflict(SubscriptionDomainError):
    code = "usage_conflict"


class InvalidAgentTransition(SubscriptionDomainError):
    code = "invalid_agent_transition"
