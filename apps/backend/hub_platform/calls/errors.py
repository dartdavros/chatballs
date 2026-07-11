class CallDomainError(Exception):
    code = "CALL_ERROR"


class CallAccessDenied(CallDomainError):
    code = "CALL_ACCESS_DENIED"


class CallConflict(CallDomainError):
    code = "CALL_CONFLICT"


class CallInvalidTransition(CallDomainError):
    code = "CALL_INVALID_TRANSITION"


class CallTokenError(CallDomainError):
    code = "CALL_TOKEN_INVALID"
