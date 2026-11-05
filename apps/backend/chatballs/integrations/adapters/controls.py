"""UI-контролы схемных полей (ADR-0038 п.3; C4 code-service-adapter-registry).

Общий интерфейс рисует поле по ключу контрола; ключи совпадают с
компонентами internal-ui (features/integrations/services/connect/SchemaFields).
Нестандартный контрол добавляется доверенным пакетом вместе с компонентом под
новым ключом и версией — существующие ключи не меняют смысл.
"""

from __future__ import annotations

from dataclasses import dataclass

from chatballs.integrations.adapters.registry import Extension


@dataclass(frozen=True)
class Control:
    # Каким типам схемы контрол подходит.
    types: frozenset[str]


CONTROLS: dict[str, Control] = {
    "scenario_settings": Control(frozenset({"json"})),
    "structured_value": Control(frozenset({"json"})),
    "text": Control(frozenset({"string"})),
    "textarea": Control(frozenset({"string"})),
    "url": Control(frozenset({"string"})),
    "secret": Control(frozenset({"string"})),
    "number": Control(frozenset({"integer", "number"})),
    "toggle": Control(frozenset({"boolean"})),
    "select": Control(frozenset({"enum"})),
    "lookup": Control(frozenset({"lookup"})),
    "date": Control(frozenset({"date", "datetime"})),
    "file": Control(frozenset({"file"})),
}


def builtin_extensions() -> list[Extension]:
    return [Extension("control", key, 1, control) for key, control in CONTROLS.items()]
