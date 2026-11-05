"""Current guards for a manual action; unsupported state never passes silently."""

import operator

from chatballs.integrations.execution.permissions import ExecutionDenied, context_values
from chatballs.integrations.execution.source_support import require_supported_sources
from chatballs.integrations.scenarios.values import RunValues, resolve_value


def evaluate_conditions(document, conversation, parameters, *, registry=None, values=None):
    require_supported_sources(document)
    values = values or RunValues(parameters=parameters, context=context_values(conversation))
    def check(condition):
        kind = condition.get("kind")
        if kind == "context_present":
            try:
                value = resolve_value({"source": "context", "path": condition["path"]}, values, registry)
                present = value is not None
            except (KeyError, TypeError, ValueError):
                present = False
            return present == condition.get("present", True)
        if kind == "channel":
            return bool(conversation and conversation.connection_id == condition["connection"]) == condition["present"]
        if kind == "tag" and condition["scope"] == "conversation":
            return bool(conversation and conversation.labels.filter(pk=condition["tag"]).exists()) == condition["present"]
        if kind in {"has_link", "no_link"}:
            from chatballs.integrations.scenarios.entity_links import has_link
            return has_link(conversation, condition["connection"], condition["entity"]) == (kind == "has_link")
        if kind is not None:
            # Entity-link/contact-label evaluation belongs to its real domain
            # implementation; absence is not evidence that a link is absent.
            raise ExecutionDenied("conditions_unavailable")
        try:
            left = resolve_value(condition["left"], values, registry)
            op = condition["op"]
            if op in {"empty", "filled"}:
                empty = left is None or left == "" or left == [] or left == {}
                return empty if op == "empty" else not empty
            right = resolve_value(condition["right"], values, registry)
            comparisons = {"eq": operator.eq, "ne": operator.ne, "gt": operator.gt, "gte": operator.ge,
                           "lt": operator.lt, "lte": operator.le, "contains": lambda a, b: b in a}
            return comparisons[op](left, right)
        except (KeyError, ValueError, TypeError, IndexError):
            raise ExecutionDenied("arguments") from None
    conditions = document["conditions"]
    # No short-circuit may hide an unsupported guard and later admit it.
    results = [check(condition) for condition in conditions["items"]]
    accepted = not results or (all(results) if conditions["mode"] == "all" else any(results))
    return accepted


def require_conditions(document, conversation, parameters, *, registry=None, values=None):
    if not evaluate_conditions(document, conversation, parameters, registry=registry, values=values):
        raise ExecutionDenied("conditions_not_met")
