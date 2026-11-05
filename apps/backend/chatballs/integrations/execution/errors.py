"""Only known, localized codes cross the execution API boundary."""

from chatballs.i18n import t

KNOWN = frozenset({
    "budget_depth", "budget_execution", "budget_iterations", "budget_volume", "recursion", "calendar_unavailable",
    "version_incompatible", "approval_expired", "approval_changed", "permission",
    "connection_paused", "scenario_disabled", "arguments", "context_changed",
    "context", "conditions_not_met", "conditions_unavailable", "composition_unavailable",
    "data_cleared", "state_changed", "retention_values", "retention_confirmation",
    "site_event_suppressed", "site_event_failed",
})


def error_message(code):
    return t(f"runs.error_{code}") if code in KNOWN else t("runs.unavailable")
