"""Inventory mounted socket lifecycles and actual dispatch frame names."""

import ast
import inspect


def _type_expression(node):
    return isinstance(node, ast.Name) and node.id == "msg_type" or (
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name) and node.func.value.id == "content"
        and node.func.attr == "get" and node.args
        and isinstance(node.args[0], ast.Constant) and node.args[0].value == "type")


def _frames(consumer):
    frames = set()
    for cls in consumer.__mro__:
        if not cls.__module__.startswith("chatballs."):
            continue
        frames.update(getattr(inspect.getmodule(cls), "RELAY_TYPES", ()))
        for node in ast.walk(ast.parse(inspect.getsource(cls))):
            if isinstance(node, ast.Compare) and _type_expression(node.left):
                frames.update(other.value for other in node.comparators
                    if isinstance(other, ast.Constant) and isinstance(other.value, str))
    return frames


def mounted_protocol_entries():
    from chatballs_backend.asgi_app import application

    entries = set()
    for route in application.application_mapping["websocket"].routes:
        callback = route.callback
        seen = set()
        while callback is not None and not hasattr(callback, "consumer_class") and id(callback) not in seen:
            seen.add(id(callback))
            callback = getattr(callback, "inner", None)
        consumer = getattr(callback, "consumer_class", None)
        path = str(route.pattern)
        if consumer is None:
            entries.add((path, "UNKNOWN", ""))
            continue
        handler = f"{consumer.__module__}.{consumer.__name__}"
        entries.update((path, lifecycle, handler) for lifecycle in ("CONNECT", "DISCONNECT"))
        entries.update((path, f"WS:{frame}", handler) for frame in _frames(consumer))
    return entries
