"""Preset metadata and its canonical scenario definition (no second executor)."""

from dataclasses import dataclass, field
from typing import Any

from chatballs.integrations.adapters.schema import TypeSpec


@dataclass(frozen=True)
class TemplateStep:
    id: str
    title_key: str
    target: str
    inputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioTemplate:
    key: str
    version: int
    title_key: str
    purpose_key: str
    parameters: TypeSpec = TypeSpec("object")
    steps: tuple[TemplateStep, ...] = ()
    triggers: tuple[dict[str, Any], ...] = ()
    conditions: tuple[dict[str, Any], ...] = ()
    required_connections: tuple[str, ...] = ("self",)
    required_permissions: tuple[str, ...] = ()
    # Complete versioned document for composite presets. T-168's action-only
    # shorthand is converted once on copying, never interpreted by a runner.
    definition: dict[str, Any] | None = None
    # Presentation only: canonical document paths to catalogue keys.
    labels: tuple[tuple[str, str], ...] = ()
