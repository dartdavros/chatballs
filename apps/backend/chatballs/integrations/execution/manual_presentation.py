"""Navigation metadata is explicit and never participates in authorization."""

import json

from chatballs.i18n import t
from chatballs.integrations.scenarios.types import read_type
from chatballs.integrations.service_connections.payloads import field_payload


def parameter_schema(data):
    result = field_payload("", read_type(data))

    def titles(field, schema):
        if schema.get("title"):
            field["title"] = schema["title"]
        for child in field.get("fields", []):
            titles(child, schema.get("properties", {}).get(child["name"], {}))
        if field.get("items"):
            titles(field["items"], schema.get("items", {}))
    titles(result, data)
    return result


def scenario_presentation(row):
    path = getattr(row, "category_path", [])
    categories = [{"key": json.dumps(path[:index + 1], ensure_ascii=False), "title": title}
                  for index, title in enumerate(path)]
    return {"source": {"key": "scenarios", "title": t("runs.catalog_scenarios"), "kind": "scenarios"},
            "categoryPath": categories or [{"key": "uncategorized", "title": t("runs.catalog_uncategorized")}]}


def service_presentation(connection, adapter, operation):
    return {"source": {"key": f"service:{connection.pk}", "title": t(adapter.presentation.title_key),
                       "subtitle": connection.name, "kind": "service"},
            "categoryPath": [{"key": category.key, "title": t(category.title_key)} for category in operation.category_path]}


def native_presentation():
    return {"source": {"key": "native", "title": t("runs.catalog_native"), "kind": "native"}, "categoryPath": []}
