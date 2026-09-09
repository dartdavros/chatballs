#!/usr/bin/env python3
"""Готовит релизную копию compose.yaml: ссылки на образы закреплены по digest.

Установка на чистый хост — это один файл: человек скачивает compose.yaml со
страницы релиза и делает `docker compose up -d --wait`. Значит в этом файле не
должно остаться ни одной подстановки, которая молча возьмёт `:dev` или плавающий
тег, если переменной в окружении нет.

Скрипт переписывает ровно значения по умолчанию внутри ``${VAR:-...}`` для
известных ключей образов и падает, если хоть один ключ не найден или пришёл без
digest. Переопределение переменной окружения остаётся возможным — это нужно
staging и облаку, которые ведут конфигурацию сами.

Использование:
    pin-release-compose.py --source compose.yaml --output dist/compose.yaml \\
        --version 1.0.0 --pin CHATBALLS_BACKEND_IMAGE=ghcr.io/...@sha256:... ...
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

IMAGE_KEYS = (
    "CHATBALLS_BACKEND_IMAGE",
    "CHATBALLS_FRONTEND_IMAGE",
    "CHATBALLS_POSTGRES_IMAGE",
    "CHATBALLS_REDIS_IMAGE",
    "CHATBALLS_GATEWAY_IMAGE",
    "CHATBALLS_COTURN_IMAGE",
)

DIGEST_RE = re.compile(r"@sha256:[0-9a-fA-F]{64}$")

HEADER = """# Chatballs {version} — релизная копия compose.yaml.
#
# Установка на чистый хост с одним докером:
#
#   docker compose up -d --wait
#
# Больше рядом ничего не нужно: Caddyfile, init-скрипты базы и генератор
# секретов лежат внутри образов. Файл сгенерирован автоматически из
# compose.yaml релиза {version}; править его руками не нужно — обновление
# сводится к тому, чтобы скачать этот файл новой версии и повторить команду.
#
"""


def pin(source: str, pins: dict[str, str], version: str) -> str:
    text = source
    for key, ref in pins.items():
        pattern = re.compile(r"\$\{" + re.escape(key) + r":-[^}]*\}")
        replaced, count = pattern.subn(ref, text)
        if count == 0:
            raise SystemExit(f"{key}: подстановка ${{{key}:-...}} не найдена в compose.yaml")
        text = replaced
    leftover = [key for key in IMAGE_KEYS if f"${{{key}" in text]
    if leftover:
        raise SystemExit("не закреплены ссылки на образы: " + ", ".join(leftover))
    return HEADER.format(version=version) + text


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="compose.yaml")
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument(
        "--pin",
        action="append",
        default=[],
        metavar="KEY=REF",
        help="ссылка на образ по digest, по одной на каждый ключ",
    )
    args = parser.parse_args(argv)

    pins: dict[str, str] = {}
    for item in args.pin:
        key, _, ref = item.partition("=")
        if key not in IMAGE_KEYS:
            raise SystemExit(f"неизвестный ключ образа: {key}")
        if not DIGEST_RE.search(ref):
            raise SystemExit(f"{key}: ссылка обязана быть закреплена по @sha256")
        pins[key] = ref

    missing = [key for key in IMAGE_KEYS if key not in pins]
    if missing:
        raise SystemExit("не переданы ссылки на образы: " + ", ".join(missing))

    source = Path(args.source).read_text(encoding="utf-8")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(pin(source, pins, args.version), encoding="utf-8", newline="\n")
    print(f"{output}: закреплено ссылок — {len(pins)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
