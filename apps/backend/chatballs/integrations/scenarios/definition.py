"""Versioned scenario document, shared by presets, editor and execution.

The document contains no tenant, credentials or executable user code. Revision
and ownership belong to persistence. Saving a definition has no runtime effects.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chatballs.integrations.adapters.schema import TypeSpec

FORMAT_VERSION = 1
BLOCK_KINDS = frozenset({"action", "if", "foreach", "parallel", "call", "wait", "try"})
TRIGGER_KINDS = frozenset({"staff", "ai", "chatballs", "service", "schedule", "api", "scenario"})
BINDING_SOURCES = frozenset({"constant", "input", "parameter", "context", "event", "step", "item", "error"})


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}", value) is not None


@dataclass(frozen=True)
class Issue:
    path: str
    code: str


@dataclass
class DefinitionContext:
    """Server supplied schemas; never taken from the submitted document."""

    operations: dict[tuple[str, str], tuple[TypeSpec, TypeSpec]] = field(default_factory=dict)
    scenarios: dict[str, tuple[TypeSpec, TypeSpec]] = field(default_factory=dict)
    events: dict[tuple[str, str], TypeSpec] = field(default_factory=dict)
    context: TypeSpec = field(default_factory=lambda: TypeSpec("object"))
    files: set[str] = field(default_factory=set)
    connections: set[str] = field(default_factory=set)
    entities: dict[tuple[str, str], TypeSpec] = field(default_factory=dict)
    writable_fields: dict[tuple[str, str], set[str]] = field(default_factory=dict)
    staff: set[int] = field(default_factory=set)
    groups: set[int] = field(default_factory=set)
    agents: set[int] = field(default_factory=set)
    labels: set[int] = field(default_factory=set)
    channels: set[int] = field(default_factory=set)


def empty_definition() -> dict[str, Any]:
    return {
        "version": FORMAT_VERSION,
        "parameters": {"type": "object", "properties": {}},
        "results": {"type": "object", "properties": {}},
        "outputs": {},
        "triggers": [{"id": "staff", "kind": "staff"}],
        "conditions": {"mode": "all", "items": []},
        "steps": [],
        "access": {"staff": [], "groups": [], "aiMode": "confirm", "delegated": False,
                   "scope": "conversation", "confirm": "effects"},
        "synchronization": [],
    }


def child_lists(step: dict) -> list[tuple[str, list]]:
    kind = step.get("kind")
    keys = {"if": ("then", "else"), "foreach": ("body",), "try": ("body", "catch")}.get(kind, ())
    children = [(key, step[key]) for key in keys if isinstance(step.get(key), list)]
    if kind == "parallel" and isinstance(step.get("branches"), list):
        children += [(f"branches.{i}", branch) for i, branch in enumerate(step["branches"]) if isinstance(branch, list)]
    return children
