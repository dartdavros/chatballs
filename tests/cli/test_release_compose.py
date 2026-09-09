"""compose.yaml обязан быть самодостаточным: установка — один файл.

Раньше стек монтировал с хоста Caddyfile, init-скрипты базы и генератор
секретов. Из-за этого установка требовала рядом распакованный репозиторий, а
файл, забытый при сборке релиза, Docker молча подменял пустым каталогом — и
стек падал на первом старте, уже у человека.

Эти тесты держат свойство, а не текущий текст файла: в production-манифесте нет
ни одного bind-mount (кроме сертификатов TURN у опционального профиля calls), а
все ссылки на образы поддаются закреплению по digest.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / "compose.yaml"
PIN_SCRIPT = REPO_ROOT / "scripts" / "pin-release-compose.py"

# Единственное исключение: сертификат TURN-хоста кладёт на хост renewal-хук,
# и только при включённом профиле calls.
BIND_MOUNT_EXCEPTIONS = {"coturn"}

DIGEST = "sha256:" + "a" * 64
IMAGE_KEYS = (
    "CHATBALLS_BACKEND_IMAGE",
    "CHATBALLS_FRONTEND_IMAGE",
    "CHATBALLS_POSTGRES_IMAGE",
    "CHATBALLS_REDIS_IMAGE",
    "CHATBALLS_GATEWAY_IMAGE",
    "CHATBALLS_COTURN_IMAGE",
)


def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def _volume_source(entry) -> str:
    if isinstance(entry, str):
        return entry.split(":", 1)[0]
    return str(entry.get("source", ""))


def _is_bind(source: str) -> bool:
    """Bind-mount — всё, что указывает на путь, а не на именованный том."""
    return source.startswith((".", "/", "~")) or "${" in source


@pytest.mark.parametrize("service", sorted(_compose()["services"]))
def test_service_has_no_host_bind_mounts(service: str) -> None:
    definition = _compose()["services"][service]
    binds = [
        source
        for entry in definition.get("volumes", [])
        if _is_bind(source := _volume_source(entry))
    ]
    if service in BIND_MOUNT_EXCEPTIONS:
        pytest.skip(f"{service}: bind-mount разрешён явно")
    assert binds == [], (
        f"{service}: манифест монтирует с хоста {binds}. "
        "Установка — один compose.yaml: всё, что нужно сервису, кладётся в образ."
    )


def test_named_volumes_are_declared() -> None:
    compose = _compose()
    declared = set(compose.get("volumes") or {})
    used = {
        source
        for definition in compose["services"].values()
        for entry in definition.get("volumes", [])
        if not _is_bind(source := _volume_source(entry))
    }
    assert used <= declared, f"не объявлены тома: {sorted(used - declared)}"


def test_every_image_reference_can_be_pinned(tmp_path: Path) -> None:
    """Все шесть ключей образов присутствуют и закрепляются по digest.

    Если из манифеста уйдёт (или переименуется) хоть один ключ, релизный
    compose.yaml уедет с плавающим тегом — а найдётся это уже у человека.
    """
    output = tmp_path / "compose.yaml"
    pins: list[str] = []
    for key in IMAGE_KEYS:
        pins += ["--pin", f"{key}=registry.test/{key.lower()}:1.0.0@{DIGEST}"]

    result = subprocess.run(
        [sys.executable, str(PIN_SCRIPT), "--source", str(COMPOSE),
         "--output", str(output), "--version", "1.0.0-test", *pins],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    pinned = output.read_text(encoding="utf-8")
    for key in IMAGE_KEYS:
        assert f"${{{key}" not in pinned, f"{key} остался подстановкой в релизном файле"


def test_pinning_rejects_floating_tag(tmp_path: Path) -> None:
    pins: list[str] = []
    for key in IMAGE_KEYS:
        ref = "registry.test/x:1.0.0" if key == "CHATBALLS_BACKEND_IMAGE" else f"registry.test/x:1.0.0@{DIGEST}"
        pins += ["--pin", f"{key}={ref}"]

    result = subprocess.run(
        [sys.executable, str(PIN_SCRIPT), "--source", str(COMPOSE),
         "--output", str(tmp_path / "compose.yaml"), "--version", "1.0.0-test", *pins],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "@sha256" in result.stdout + result.stderr
