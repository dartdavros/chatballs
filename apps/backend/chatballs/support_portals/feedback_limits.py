"""Native feedback uses the product rate with an authenticated actor identity."""

from rest_framework.throttling import SimpleRateThrottle

FEEDBACK_SCOPE = "help_feedback"


class NativeFeedbackThrottle(SimpleRateThrottle):
    scope = FEEDBACK_SCOPE

    def __init__(self, context):
        self.identity = f"native:{context.organization_id}:{context.membership_id}"
        super().__init__()

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.identity}


def allow_native_feedback(context):
    # No visitor IP is invented: native runs are charged to their real actor.
    return NativeFeedbackThrottle(context).allow_request(None, None)
