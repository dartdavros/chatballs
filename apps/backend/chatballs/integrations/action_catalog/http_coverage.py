"""Enumerate both product surfaces, including inherited and framework methods."""

from django.urls import URLResolver, get_resolver
from django.utils.module_loading import import_string
from django.views import View
from rest_framework.views import APIView

SURFACES = {"app": "chatballs_backend.urls_app", "platform": "chatballs_backend.urls_platform"}
METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"})


def mounted_http_entries():
    def walk(patterns, surface, prefix=""):
        for pattern in patterns:
            route = prefix + str(pattern.pattern)
            if isinstance(pattern, URLResolver):
                yield from walk(pattern.url_patterns, surface, route)
                continue
            callback = pattern.callback
            view = getattr(callback, "cls", None) or getattr(callback, "view_class", None)
            if view is None:
                yield surface, route, "ANY", f"{callback.__module__}.{callback.__name__}"
                continue
            handler = f"{view.__module__}.{view.__name__}"
            allowed = getattr(callback, "initkwargs", {}).get("http_method_names", view.http_method_names)
            actions = getattr(callback, "actions", {})
            for method in sorted(METHODS):
                if method.lower() not in allowed:
                    continue
                if (hasattr(view, method.lower()) or method.lower() in actions
                        or method == "HEAD" and hasattr(view, "get")):
                    yield surface, route, method, handler
    return {entry for surface, urlconf in SURFACES.items()
        for entry in walk(get_resolver(urlconf).url_patterns, surface)}


def framework_entries(rows):
    """Only proven framework aliases; custom HEAD/OPTIONS stay unclassified."""
    seen = {(r.get("surface", "app"), r["route"], r["method"], r["handler"]) for r in rows}
    for row in rows:
        if row["method"] not in METHODS - {"HEAD", "OPTIONS"}:
            continue
        try:
            view = import_string(row["handler"])
        except (ImportError, AttributeError):
            continue
        if not isinstance(view, type) or not issubclass(view, View):
            continue
        aliases = []
        if row["method"] == "GET" and not hasattr(view, "head") and "head" in view.http_method_names:
            aliases.append(("HEAD", "Framework HEAD delegates to this exact GET and suppresses the response body; no independent operation."))
        if getattr(view, "options", None) in (APIView.options, View.options) and "options" in view.http_method_names:
            aliases.append(("OPTIONS", "Unmodified Django View.options or DRF APIView.options: allowed methods/schema metadata; no domain effect."))
        for method, reason in aliases:
            key = row.get("surface", "app"), row["route"], method, row["handler"]
            if key not in seen:
                seen.add(key)
                yield {"surface": key[0], "route": key[1], "method": method, "handler": key[3],
                    "action": None, "classification": "transport", "reason": reason,
                    "evidence": ["apps/backend/chatballs/integrations/action_catalog/http_coverage.py",
                        *row.get("evidence", [])]}
