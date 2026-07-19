"""Разбор тел запросов API каналов (SPEC-HUB-0027 §6.3, §6.5).

Отделено от views, чтобы представления оставались тонкими: проверка формы —
здесь, доменные правила — в services, авторизация — в authorization.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError

from hub_platform.channels.policy import (
    POLICY_API_FIELDS,
    ChannelPolicy,
    PolicyPreset,
)
from hub_platform.channels.services import UNSET, ChannelUpdate


def _optional_id(data: dict, key: str, current=UNSET):
    if key not in data:
        return current
    value = data[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError({key: f"{key} must be an integer or null"})
    return value


def _optional_bool(data: dict, key: str):
    if key not in data:
        return UNSET
    value = data[key]
    if not isinstance(value, bool):
        raise ValidationError({key: f"{key} must be a boolean"})
    return value


def parse_policy_fields(raw: object) -> dict[str, bool]:
    """camelCase-ключи политики -> поля модели. Неизвестные ключи отвергаются."""
    if not isinstance(raw, dict):
        raise ValidationError({"policy": "policy must be an object"})
    unknown = set(raw) - set(POLICY_API_FIELDS)
    if unknown:
        raise ValidationError({"policy": f"Неизвестные флаги: {', '.join(sorted(unknown))}"})
    fields: dict[str, bool] = {}
    for key, value in raw.items():
        if not isinstance(value, bool):
            raise ValidationError({"policy": f"{key} must be a boolean"})
        fields[POLICY_API_FIELDS[key]] = value
    return fields


def parse_create_policy(data: dict) -> ChannelPolicy:
    """§6.3: policyPreset и policy взаимоисключающи, CUSTOM требует policy."""
    preset = data.get("policyPreset")
    has_policy = "policy" in data
    if preset is None and not has_policy:
        raise ValidationError({"policy": "Укажите policyPreset или policy"})
    if preset in {PolicyPreset.SALES, PolicyPreset.SUPPORT}:
        if has_policy:
            raise ValidationError(
                {"policy": "policyPreset и policy взаимоисключающи"}
            )
        return ChannelPolicy.from_preset(preset)
    if preset == PolicyPreset.CUSTOM and not has_policy:
        raise ValidationError({"policy": "Пресет CUSTOM требует policy"})
    if preset is not None and preset != PolicyPreset.CUSTOM:
        raise ValidationError({"policyPreset": f"Неизвестный пресет: {preset}"})

    fields = parse_policy_fields(data.get("policy"))
    missing = set(POLICY_API_FIELDS.values()) - set(fields)
    if missing:
        raise ValidationError({"policy": "Политика задаётся всеми пятью флагами"})
    return ChannelPolicy(**fields)


def parse_connection_ids(raw: object) -> list[int]:
    if raw is None:
        return []
    if not isinstance(raw, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in raw
    ):
        raise ValidationError({"connectionIds": "connectionIds must be a list of integers"})
    return list(dict.fromkeys(raw))


def parse_update(data: dict, *, current_code: str) -> ChannelUpdate:
    """§6.5: code в теле игнорируется, другое значение — 400."""
    if "code" in data and str(data["code"] or "").strip() != current_code:
        raise ValidationError({"code": "Код канала не изменяется после создания"})
    return ChannelUpdate(
        name=data["name"] if "name" in data else UNSET,
        department_id=_optional_id(data, "departmentId"),
        product_id=_optional_id(data, "productId"),
        is_active=_optional_bool(data, "isActive"),
        policy=parse_policy_fields(data["policy"]) if "policy" in data else {},
    )
