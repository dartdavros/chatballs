"""Presentation paths cannot replace scenario behavior or literal business data."""

import re

_STEP_NAME = re.compile(r"/steps/\d+/(?:(?:(?:then|else|body|catch)/\d+|branches/\d+/\d+)/)*name")
_SCHEMA_TITLE = re.compile(r"/(?:parameters|results)/(?:properties/[^/]+/|items/)*title")


def label_target(document, path):
    if not isinstance(path, str) or not (_STEP_NAME.fullmatch(path) or _SCHEMA_TITLE.fullmatch(path)):
        raise ValueError("label path must address a step name or schema title")
    parts = path[1:].split("/")
    node = document
    try:
        for part in parts[:-1]:
            node = node[int(part)] if isinstance(node, list) else node[part]
    except (KeyError, IndexError, TypeError, ValueError):
        raise ValueError("label path does not exist") from None
    if not isinstance(node, dict) or not isinstance(node.get(parts[-1], ""), str):
        raise ValueError("label must be text")
    return node, parts[-1]
