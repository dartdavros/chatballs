"""Deferred domain sources are unavailable, never evidence of absence."""

from chatballs.integrations.execution.permissions import ExecutionDenied


def _context_path(path):
    if path == "conversation.topic" or path.startswith("conversation.topic."):
        raise ExecutionDenied("conditions_unavailable")


def _binding(value):
    if isinstance(value, list):
        for child in value:
            _binding(child)
    elif isinstance(value, dict):
        source = value.get("source")
        if isinstance(source, str):
            if source == "context":
                path = value.get("path", "")
                if value.get("transform") == "object.get@1":
                    path = ".".join(part for part in (path, value.get("args", {}).get("path", "")) if part)
                _context_path(path)
            # Constant values and transform arguments are literal data, not
            # nested bindings that may be interpreted as a domain dependency.
            return
        for child in value.values():
            _binding(child)


def require_supported_sources(document):
    for condition in document["conditions"]["items"]:
        kind = condition.get("kind")
        if kind == "context_present":
            _context_path(condition["path"])
        elif kind == "tag" and condition["scope"] != "conversation":
            raise ExecutionDenied("conditions_unavailable")
        elif kind not in {None, "tag", "channel", "has_link", "no_link"}:
            # EntityLink and any unknown domain predicate remain blocked.
            raise ExecutionDenied("conditions_unavailable")
        if kind is None:
            _binding(condition.get("left"))
            _binding(condition.get("right"))
    from chatballs.integrations.scenarios.definition import child_lists
    for block in document.get("steps", []):
        _binding(block.get("inputs", {}))
        _binding(block.get("list"))
        _binding(block.get("until"))
        if block.get("condition"):
            require_supported_sources({"conditions": block["condition"], "steps": []})
        for _, children in child_lists(block):
            require_supported_sources({"conditions": {"mode": "all", "items": []}, "steps": children})
