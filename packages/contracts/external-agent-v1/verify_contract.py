"""Локальная проверка артефакта; не запускает API, сеть, backend или fixtures."""

from copy import deepcopy
from decimal import Decimal
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012


ROOT = Path(__file__).resolve().parent
ENTRY = ROOT.parent / "external-agent-v1.openapi.yaml"


class UniqueLoader(yaml.SafeLoader):
    """Повтор ключа в YAML — ошибка документа, а не молчаливое замещение."""


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"Повтор ключа YAML: {key}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)


def read(path):
    return yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)


def visit_refs(value, base_uri, documents):
    from urllib.parse import unquote, urljoin, urldefrag

    if isinstance(value, dict):
        if "$ref" in value:
            absolute = urljoin(base_uri, value["$ref"])
            document_uri, pointer = urldefrag(absolute)
            if document_uri not in documents:
                raise ValueError(f"Нелокальная/отсутствующая ссылка: {absolute}")
            target = documents[document_uri]
            for token in unquote(pointer).lstrip("/").split("/") if pointer else []:
                target = target[token.replace("~1", "/").replace("~0", "~")]
        for child in value.values():
            visit_refs(child, base_uri, documents)
    elif isinstance(value, list):
        for child in value:
            visit_refs(child, base_uri, documents)


def schema_validator(reference, registry):
    name, pointer = reference.split("#", 1)
    uri = (ROOT / name).as_uri()
    schema = {"$ref": uri + "#" + pointer}
    return Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())


def mutate(value, changes):
    result = deepcopy(value)
    for path, new_value in changes.get("set", {}).items():
        target = result
        keys = path.split(".")
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = new_value
    for path in changes.get("remove", []):
        target = result
        keys = path.split(".")
        for key in keys[:-1]:
            target = target[key]
        del target[keys[-1]]
    return result


def canonical(text):
    """Проверочный алгоритм документа; не импортируется приложением."""
    def tree(value):
        if value is None:
            return ["null"]
        if isinstance(value, bool):
            return ["boolean", value]
        if isinstance(value, str):
            return ["string", value]
        if isinstance(value, Decimal):
            sign, digits, exponent = value.as_tuple()
            coefficient = "".join(map(str, digits)).lstrip("0")
            if not coefficient:
                return ["number", "0e0"]
            while coefficient.endswith("0"):
                coefficient, exponent = coefficient[:-1], exponent + 1
            return ["number", f"{'-' if sign else ''}{coefficient}e{exponent}"]
        if isinstance(value, list):
            return ["array", [tree(item) for item in value]]
        return ["object", [[key, tree(value[key])] for key in sorted(value)]]

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Повтор ключа JSON")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError(f"Недопустимое число JSON: {value}")

    value = json.loads(text, parse_int=Decimal, parse_float=Decimal,
                       parse_constant=invalid_number, object_pairs_hook=pairs)
    return json.dumps(tree(value), ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    paths = [ENTRY, *sorted(ROOT.glob("*.yaml"))]
    documents = {path.as_uri(): read(path) for path in paths}
    for uri, document in documents.items():
        visit_refs(document, uri, documents)
    # Валидатор читает только заранее проверенные локальные $ref.
    validate(documents[ENTRY.as_uri()], base_uri=ENTRY.as_uri())
    registry = Registry().with_resources(
        (uri, Resource.from_contents(doc, default_specification=DRAFT202012))
        for uri, doc in documents.items()
    )
    examples = documents[(ROOT / "examples.yaml").as_uri()]
    prepared = []
    for example in examples["valid"]:
        if "fromValid" in example:
            original = prepared[example["fromValid"]]
            reference = original["schema"]
            value = mutate(original["value"], example)
        else:
            reference, value = example["schema"], example["value"]
        schema_validator(reference, registry).validate(value)
        prepared.append({"schema": reference, "value": value})
    for example in examples["invalid"]:
        if "fromValid" in example:
            original = prepared[example["fromValid"]]
            reference = original["schema"]
            value = mutate(original["value"], example)
        else:
            reference, value = example["schema"], example["value"]
        if schema_validator(reference, registry).is_valid(value):
            raise AssertionError(f"Не отклонён пример: {example['name']}")
    vectors = documents[(ROOT / "canonicalization.yaml").as_uri()]["vectors"]
    for vector in vectors:
        left, right = canonical(vector["left"]), canonical(vector["right"])
        if (left == right) != vector["equal"] or left != vector["canonical"].encode("utf-8"):
            raise AssertionError(f"Нарушена канонизация: {vector['name']}")
    operations = 0
    for item in documents[ENTRY.as_uri()]["paths"].values():
        name, pointer = item["$ref"].split("#", 1)
        item = documents[(ENTRY.parent / name).resolve().as_uri()][pointer.lstrip("/")]
        operations += sum(method in item for method in ("get", "post"))
    if operations != 12:
        raise AssertionError(f"Ожидалось 12 операций, получено {operations}")
    print(f"OpenAPI валиден; {operations} операций; "
          f"{len(examples['valid'])} допустимых и {len(examples['invalid'])} "
          f"недопустимых примеров; {len(vectors)} векторов канонизации. Runtime не проверялся.")


if __name__ == "__main__":
    main()
